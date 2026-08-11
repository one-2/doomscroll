import { notFound } from "next/navigation";
import Feed from "../feed";
import { page } from "@/lib/db";
import { feedOf, isFeed } from "@/lib/feeds";

// No generateStaticParams: it prerenders the route at build time, which would
// freeze the posts. Every feed page is a live query.
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ feed: string }> }) {
  const { feed } = await params;
  const entry = feedOf(feed);
  if (!entry) return {};
  return {
    title: `Feed — ${entry.label}`,
    description: entry.note,
    alternates: { types: { "application/rss+xml": `/${entry.slug}/feed.xml` } },
  };
}

export default async function FeedPage({ params }: { params: Promise<{ feed: string }> }) {
  const { feed } = await params;
  if (!isFeed(feed)) notFound();
  return <Feed slug={feed} initial={await page(feed)} />;
}
