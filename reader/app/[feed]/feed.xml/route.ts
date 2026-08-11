import { recent } from "@/lib/db";
import { dayOf, timeOf } from "@/lib/time";
import { feedOf, isFeed } from "@/lib/feeds";
import { readTitle, tidy } from "@/lib/titles";

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

const escape = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export async function GET(
  request: Request,
  { params }: { params: Promise<{ feed: string }> },
) {
  const { feed } = await params;
  if (!isFeed(feed)) return new Response("Not found", { status: 404 });

  const entry = feedOf(feed)!;
  const posts = await recent(feed, 50);
  const site = origin(request);

  const items = posts.map((post) => {
    // What the post read is the item title: a reader's list view is otherwise
    // ten rows of the same timestamp with nothing to tell them apart. Posts
    // that read nothing fall back to the stamp, which is all `nothing` has.
    const named = readTitle(post.reads);
    const title = named || `${dayOf(post.created_at)} \u00b7 ${timeOf(post.created_at)}`;
    const read =
      post.reads?.length > 0
        ? `<p><em>read ${escape(post.reads.map(tidy).join(" \u00b7 "))}</em></p>`
        : "";
    // No separate ]]> guard: escape() turns every > into &gt; first, so the
    // sequence cannot survive to close the section. Guarding beforehand would
    // only get its own & escaped, and the post would show a literal ]]&gt;.
    const paragraphs = post.body
      .split(/\n\s*\n/)
      .map((p) => `<p>${escape(p)}</p>`)
      .join("");
    return `    <item>
      <title>${escape(title)}</title>
      <link>${site}/${feed}#${post.id}</link>
      <guid isPermaLink="false">${site}/${feed}/post/${post.id}</guid>
      <pubDate>${new Date(post.created_at).toUTCString()}</pubDate>
      <description><![CDATA[${read}${paragraphs}]]></description>
    </item>`;
  });

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Feed — ${escape(entry.label)}</title>
    <link>${site}/${feed}</link>
    <atom:link href="${site}/${feed}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>${escape(entry.note)}</description>
    <language>en</language>
${posts.length > 0 ? `    <lastBuildDate>${new Date(posts[0].created_at).toUTCString()}</lastBuildDate>` : ""}
${items.join("\n")}
  </channel>
</rss>
`;

  return new Response(xml, {
    headers: {
      "content-type": "application/rss+xml; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
