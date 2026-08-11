/** The five feeds. `slug` is the URL and the database value; order is tab order. */
export const FEEDS = [
  { slug: "mixed", label: "Mixed", note: "Draws from all three pools at once." },
  { slug: "academic", label: "Academic", note: "Draws from research papers." },
  { slug: "creative", label: "Creative", note: "Draws from the creative corpus." },
  { slug: "news", label: "News", note: "Draws from the news feeds." },
  { slug: "nothing", label: "Nothing", note: "Shown nothing. Writes from memory alone." },
] as const;

export type FeedSlug = (typeof FEEDS)[number]["slug"];

export const SLUGS: string[] = FEEDS.map((f) => f.slug);

export function isFeed(slug: string): slug is FeedSlug {
  return SLUGS.includes(slug);
}

export function feedOf(slug: string) {
  return FEEDS.find((f) => f.slug === slug);
}

export const DEFAULT_FEED: FeedSlug = "mixed";
