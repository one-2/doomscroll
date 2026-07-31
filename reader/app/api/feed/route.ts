import { NextRequest, NextResponse } from "next/server";
import { page } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const raw = request.nextUrl.searchParams.get("cursor");
  const cursor = raw === null ? undefined : Number(raw);
  if (cursor !== undefined && !Number.isInteger(cursor)) {
    return NextResponse.json({ error: "bad cursor" }, { status: 400 });
  }
  return NextResponse.json({ posts: await page(cursor) });
}
