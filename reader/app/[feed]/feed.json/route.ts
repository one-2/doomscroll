import { isFeed } from "@/lib/feeds";
import { build } from "@/lib/syndication";

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ feed: string }> },
) {
  const { feed } = await params;
  if (!isFeed(feed)) return new Response("Not found", { status: 404 });
  return new Response((await build(request, feed)).json1(), {
    headers: {
      // JSON Feed's own type, not application/json: it is what readers sniff
      // for and what autodiscovery advertises.
      "content-type": "application/feed+json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
