"""One post per invocation, for one feed.

    shelf     = random slate from the feed's pools, empty for `nothing`
    context   = the feed's journal + its uncompressed posts + shelf
    tool loop = read(item_id), at most MAX_READS times
    insert    = post, reads, last_read_at; then compress if due

Feeds do not share memory. Each has its own journal, its own buffer and its
own read history.
"""

import argparse
import logging
import sys

from anthropic import Anthropic

import db
import llm
import safety
import shelf as shelf_mod
from compress import maybe_compress
from config import (
    BUFFER_MAX_TOK,
    FEEDS,
    MAX_READS,
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", required=True, choices=sorted(FEEDS))
    args = parser.parse_args()
    feed = args.feed

    if safety.killed():
        return 0

    client = llm.client()

    with db.connect() as conn:
        shelf = shelf_mod.draw(conn, feed)
        journal = db.latest_journal(conn, feed)
        buffer = db.buffer_posts(conn, feed)
        log.info("%s: shelf of %d, buffer of %d", feed, len(shelf), len(buffer))
        if not shelf and FEEDS[feed]:
            log.warning("%s draws from %s and every one of them is empty; the "
                        "entry will be written from memory alone",
                        feed, ", ".join(FEEDS[feed]))

        text, reads = generate(client, conn, journal, buffer, shelf)
        if not text:
            log.warning("%s: empty response; no post this run", feed)
            return 0
        if not safety.allows(client, text):
            return 0

        post_id = db.insert_post(conn, feed, text, approx_tokens(text))
        for position, source_id in enumerate(reads):
            db.insert_read(conn, post_id, source_id, shelf, position)
            db.mark_read(conn, source_id)
        conn.commit()
        log.info("%s: post %d written, %d read(s)", feed, post_id, len(reads))

        maybe_compress(client, conn, feed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
