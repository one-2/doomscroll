import { isFeed } from "@/lib/feeds";
import { build } from "@/lib/syndication";

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ feed: string }> },
) {
  const { feed } = await params;
  if (!isFeed(feed)) return new Response("Not found", { status: 404 });
  return new Response((await build(request, feed)).atom1(), {
    headers: {
      "content-type": "application/atom+xml; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
