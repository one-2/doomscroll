import { NextRequest, NextResponse } from "next/server";
import { page } from "@/lib/db";
import { isFeed } from "@/lib/feeds";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const feed = request.nextUrl.searchParams.get("feed") ?? "";
  if (!isFeed(feed)) {
    return NextResponse.json({ error: "unknown feed" }, { status: 400 });
  }
  const raw = request.nextUrl.searchParams.get("cursor");
  const cursor = raw === null ? undefined : Number(raw);
  if (cursor !== undefined && !Number.isInteger(cursor)) {
    return NextResponse.json({ error: "bad cursor" }, { status: 400 });
  }
  return NextResponse.json({ posts: await page(feed, cursor) });
}
