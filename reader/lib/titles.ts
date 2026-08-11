/** UbuWeb index entries carry that site's own conventions in their titles.
 *  These are display fixes only; sources.title keeps exactly what was ingested,
 *  so the ingester stays the record of what the page said. `--` is UbuWeb's
 *  author separator and `§n` is our own chunk index — both are kept. */
export function tidy(title: string): string {
  return title
    .replace(/\s*\[PDF[^\]]*\]/gi, "") // "[PDF]", "[PDF, 3.5mb]"
    .replace(/\s+"\s+/g, " ")          // a quote left unclosed mid-title
    .replace(/\s+-{1,2}\s*/g, " — ") // UbuWeb writes this as -, --, or --nospace
    .replace(/\s+/g, " ")
    .trim();
}

/** Names what a post read, for an RSS item title. Empty if it read nothing. */
export function readTitle(reads: string[] | undefined, limit = 100): string {
  const joined = (reads ?? []).map(tidy).join(" · ");
  if (joined.length <= limit) return joined;
  const cut = joined.lastIndexOf(" ", limit);
  return joined.slice(0, cut > 0 ? cut : limit).trimEnd() + "…";
}
