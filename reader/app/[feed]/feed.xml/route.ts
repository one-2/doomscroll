import { Feed } from "feed";
import { recent } from "@/lib/db";
import { dayOf, timeOf } from "@/lib/time";
import { feedOf, isFeed } from "@/lib/feeds";
import { readTitle, tidy } from "@/lib/titles";
import { safe } from "@/lib/xml";

export const dynamic = "force-dynamic";

/** RSS requires absolute URLs. Prefer the request's own host so previews and
 *  custom domains are self-consistent; fall back to the environment. */
function origin(request: Request): string {
  const host =
    request.headers.get("host") ??
    process.env.SITE_URL ??
    process.env.VERCEL_PROJECT_PRODUCTION_URL ??
    "";
  if (host.startsWith("http")) return host.replace(/\/$/, "");
  const proto =
    request.headers.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");
  return host ? `${proto}://${host}` : "";
}

const paragraphs = (text: string) =>
  safe(text)
    .split(/\n\s*\n/)
    .map((p) => `<p>${p}</p>`)
    .join("");

export async function GET(
  request: Request,
  { params }: { params: Promise<{ feed: string }> },
) {
  const { feed } = await params;
  if (!isFeed(feed)) return new Response("Not found", { status: 404 });

  const entry = feedOf(feed)!;
  const posts = await recent(feed, 50);
  const site = origin(request);

  const rss = new Feed({
    title: `Feed — ${entry.label}`,
    description: entry.note,
    id: `${site}/${feed}`,
    link: `${site}/${feed}`,
    language: "en",
    copyright: "",
    updated: posts.length > 0 ? new Date(posts[0].created_at) : undefined,
    feedLinks: { rss: `${site}/${feed}/feed.xml` },
  });

  for (const post of posts) {
    // What the post read is the item title: a reader's list view is otherwise
    // rows of the same timestamp with nothing to tell them apart. Posts that
    // read nothing fall back to the stamp, which is all `nothing` has.
    const named = readTitle(post.reads);
    const read =
      post.reads?.length > 0
        ? `<p><em>read ${safe(post.reads.map(tidy).join(" · "))}</em></p>`
        : "";
    rss.addItem({
      title: safe(
        named || `${dayOf(post.created_at)} · ${timeOf(post.created_at)}`,
      ),
      // Unchanged from the hand-written serialiser: `id` becomes the guid, so
      // existing subscribers do not see fifty posts arrive a second time.
      id: `${site}/${feed}/post/${post.id}`,
      link: `${site}/${feed}#${post.id}`,
      date: new Date(post.created_at),
      description: read + paragraphs(post.body),
    });
  }

  return new Response(rss.rss2(), {
    headers: {
      "content-type": "application/rss+xml; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
