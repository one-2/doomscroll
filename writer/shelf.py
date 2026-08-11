"""The shelf: a uniform random slate from the feed's pools, metadata only.

No relevance ranking, no retrieval. Items read by this feed within its last
READ_COOLDOWN reads are excluded; other feeds' reading does not affect it.
"""

from config import FEEDS, READ_COOLDOWN, SHELF_SIZE


def draw(conn, feed: str, size: int = SHELF_SIZE, cooldown: int = READ_COOLDOWN):
    pools = FEEDS[feed]
    if not pools:
        return []

    # Evenly across the pools rather than uniformly over their union: the pools
    # differ in size by an order of magnitude, and a union sample would let the
    # largest one crowd out the others on the mixed feed.
    per_pool = [size // len(pools)] * len(pools)
    for i in range(size - sum(per_pool)):
        per_pool[i] += 1

    rows = []
    for pool, want in zip(pools, per_pool):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, teaser FROM sources
                WHERE pool = %s
                  AND id NOT IN (
                      SELECT source_id FROM (
                          SELECT r.source_id FROM reads r
                          JOIN posts p ON p.id = r.post_id
                          WHERE p.feed = %s
                          ORDER BY r.id DESC LIMIT %s
                      ) recent
                  )
                ORDER BY random() LIMIT %s
                """,
                (pool, feed, cooldown, want),
            )
            rows.extend(cur.fetchall())
    return rows
