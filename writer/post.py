"""One post per invocation.

    day_index = (days since EPOCH_START) % 3
    shelf     = random slate from that day's pool
    context   = journal + uncompressed posts + shelf
    tool loop = read(item_id), at most MAX_READS times
    insert    = post, reads, last_read_at; then compress if due
"""

import logging
import sys
from datetime import date, datetime, timezone

from anthropic import Anthropic

import db
import llm
import safety
import shelf as shelf_mod
from compress import maybe_compress
from config import (
    BUFFER_MAX_TOK,
    EPOCH_START,
    MAX_READS,
    POOLS,
    POST_MAX_TOK,
    POST_MODEL,
    POST_TEMP,
    POST_THINKING,
    approx_tokens,
    sampling,
    thinking,
)
from prompts import READ_TOOL, SYSTEM_POST, render_post_context

log = logging.getLogger(__name__)


def day_index(today: date | None = None) -> int:
    today = today or datetime.now(timezone.utc).date()
    return (today - EPOCH_START).days % 3


def _handle_read(conn, block, offered: dict, reads: list) -> dict:
    """Return a tool_result block. Bad item_ids are errors, not exceptions."""
    result = {"type": "tool_result", "tool_use_id": block.id}
    item_id = (block.input or {}).get("item_id")

    if item_id not in offered:
        result["content"] = "No such item on the shelf."
        result["is_error"] = True
        return result
    if len(reads) >= MAX_READS:
        result["content"] = "Nothing more can be read now."
        result["is_error"] = True
        return result
    if item_id in reads:
        result["content"] = "Already read."
        result["is_error"] = True
        return result

    row = db.source_body(conn, item_id)
    if row is None:
        result["content"] = "No such item on the shelf."
        result["is_error"] = True
        return result

    reads.append(item_id)
    result["content"] = f"{row['title']}\n\n{row['body']}"
    return result


def generate(client: Anthropic, conn, journal, buffer, shelf):
    """Standard tool loop. Returns (text, ordered source ids read)."""
    offered = {item["id"]: item for item in shelf}
    reads: list[int] = []
    messages = [
        {
            "role": "user",
            "content": render_post_context(journal, buffer, shelf, BUFFER_MAX_TOK),
        }
    ]

    while True:
        response = client.messages.create(
            model=POST_MODEL,
            max_tokens=POST_MAX_TOK,
            system=SYSTEM_POST,
            messages=messages,
            tools=[READ_TOOL],
            **llm.caching(),
            **sampling(POST_TEMP),
            **thinking(POST_THINKING),
        )
        llm.log_usage("post", response)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = "".join(
                b.text for b in response.content if b.type == "text"
            ).strip()
            return text, reads

        results = [
            _handle_read(conn, b, offered, reads)
            for b in response.content
            if b.type == "tool_use"
        ]
        messages.append({"role": "user", "content": results})


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if safety.killed():
        return 0

    client = llm.client()
    index = day_index()
    pool = POOLS[index]

    with db.connect() as conn:
        shelf = shelf_mod.draw(conn, pool)
        journal = db.latest_journal(conn)
        buffer = db.buffer_posts(conn)
        log.info("day %d (%s), shelf of %d, buffer of %d", index, pool, len(shelf), len(buffer))

        text, reads = generate(client, conn, journal, buffer, shelf)
        if not text:
            log.warning("empty response; no post this run")
            return 0
        if not safety.allows(client, text):
            return 0

        post_id = db.insert_post(conn, text, index, approx_tokens(text))
        for position, source_id in enumerate(reads):
            db.insert_read(conn, post_id, source_id, shelf, position)
            db.mark_read(conn, source_id)
        conn.commit()
        log.info("post %d written, %d read(s)", post_id, len(reads))

        maybe_compress(client, conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
