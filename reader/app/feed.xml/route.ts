import { recent } from "@/lib/db";

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
  const proto = request.headers.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");
  return host ? `${proto}://${host}` : "";
}

const escape = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export async function GET(request: Request) {
  const posts = await recent(50);
  const site = origin(request);

  const items = posts.map((post) => {
    const paragraphs = post.body
      .replace(/]]>/g, "]]&gt;")     // would close the CDATA section early
      .split(/\n\s*\n/)
      .map((p) => `<p>${escape(p)}</p>`)
      .join("");
    return `    <item>
      <title>${escape(post.created_at.replace("T", " ").replace("Z", " UTC"))}</title>
      <link>${site}/#${post.id}</link>
      <guid isPermaLink="false">${site}/post/${post.id}</guid>
      <pubDate>${new Date(post.created_at).toUTCString()}</pubDate>
      <description><![CDATA[${paragraphs}]]></description>
    </item>`;
  });

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Feed</title>
    <link>${site}/</link>
    <atom:link href="${site}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>One entry a day.</description>
    <language>en</language>
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
