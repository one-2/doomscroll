"""The journal is rewritten, not appended.

Trigger: the buffer reaches BUFFER_MAX_TOK, or COMPRESS_DAYS have passed since
the last rewrite. The model is given the old journal and the whole buffer and
writes a replacement bounded by max_tokens. Output over the cap is truncated by
max_tokens; there is no retry. Old journals stay in the table but only the
newest is ever sent.
"""

import logging
from datetime import datetime, timezone

from anthropic import Anthropic

import db
import llm
from config import (
    BUFFER_MAX_TOK,
    COMPRESS_DAYS,
    COMPRESS_MODEL,
    COMPRESS_TEMP,
    COMPRESS_THINKING,
    JOURNAL_MAX_TOK,
    approx_tokens,
    sampling,
    thinking,
)
from prompts import SYSTEM_COMPRESS, render_compress_context

log = logging.getLogger(__name__)


def due(journal, buffer) -> bool:
    if not buffer:
        return False
    if sum(p["token_count"] or 0 for p in buffer) >= BUFFER_MAX_TOK:
        return True
    if COMPRESS_DAYS <= 0:      # token-driven only
        return False
    if journal is None:
        oldest = buffer[0]["created_at"]
    else:
        oldest = journal["created_at"]
    return (datetime.now(timezone.utc) - oldest).days >= COMPRESS_DAYS


def compress(client: Anthropic, conn) -> int | None:
    journal = db.latest_journal(conn)
    buffer = db.buffer_posts(conn)
    if not buffer:
        return None

    response = client.messages.create(
        model=COMPRESS_MODEL,
        max_tokens=JOURNAL_MAX_TOK,
        system=SYSTEM_COMPRESS,
        messages=[
            {"role": "user", "content": render_compress_context(journal, buffer)}
        ],
        **sampling(COMPRESS_TEMP),
        **thinking(COMPRESS_THINKING),
    )
    llm.log_usage("compress", response)
    body = "".join(b.text for b in response.content if b.type == "text").strip()
    if not body:
        log.warning("empty journal; keeping the old one")
        return None

    covers_from, covers_to = buffer[0]["id"], buffer[-1]["id"]
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO journals (body, token_count, covers_from, covers_to) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (body, approx_tokens(body), covers_from, covers_to),
        )
        journal_id = cur.fetchone()["id"]
        cur.execute(
            "UPDATE posts SET journal_id = %s WHERE journal_id IS NULL AND id <= %s",
            (journal_id, covers_to),
        )
    conn.commit()
    log.info(
        "journal %d written, %d tokens, covering posts %d-%d",
        journal_id, approx_tokens(body), covers_from, covers_to,
    )
    return journal_id


def maybe_compress(client: Anthropic, conn) -> int | None:
    journal = db.latest_journal(conn)
    buffer = db.buffer_posts(conn)
    if not due(journal, buffer):
        return None
    return compress(client, conn)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with db.connect() as conn:
        compress(llm.client(), conn)
