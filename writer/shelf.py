"""The shelf: a uniform random slate from the active pool, metadata only.

No relevance ranking, no retrieval. Items read within the last READ_COOLDOWN
reads are excluded; never-read items are always eligible.
"""

from config import READ_COOLDOWN, SHELF_SIZE


def draw(conn, pool: str, size: int = SHELF_SIZE, cooldown: int = READ_COOLDOWN):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, teaser FROM sources
            WHERE pool = %s
              AND id NOT IN (
                  SELECT source_id FROM (
                      SELECT source_id FROM reads ORDER BY id DESC LIMIT %s
                  ) recent
              )
            ORDER BY random() LIMIT %s
            """,
            (pool, cooldown, size),
        )
        return cur.fetchall()
