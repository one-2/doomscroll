"""Prompts, verbatim. No persona name, no biography, no length instruction.

The text lives in reader/prompts.json because the about page reprints it and
Vercel only deploys the reader directory. One file, so the page cannot drift
from what is actually sent.
"""

import json
from pathlib import Path

_PROMPTS = Path(__file__).parent.parent / "reader" / "prompts.json"
if not _PROMPTS.exists():
    raise RuntimeError(f"prompt file missing: {_PROMPTS}")
_TEXT = json.loads(_PROMPTS.read_text(encoding="utf-8"))

SYSTEM_POST = _TEXT["post"]
SYSTEM_COMPRESS = _TEXT["compress"]

READ_TOOL = {
    "name": "read",
    "description": "Read an item from the shelf in full.",
    "input_schema": {
        "type": "object",
        "properties": {"item_id": {"type": "integer"}},
        "required": ["item_id"],
    },
}


def render_post_context(journal, buffer, shelf, budget: int) -> str:
    """Memory first, shelf last. The buffer is truncated from the front."""
    from config import approx_tokens

    memory = journal["body"] if journal else "(nothing yet)"

    kept, spent = [], 0
    for post in reversed(buffer):          # newest first while measuring
        cost = post["token_count"] or approx_tokens(post["body"])
        if spent + cost > budget:
            break
        kept.append(post["body"])
        spent += cost
    recent = "\n\n---\n\n".join(reversed(kept)) or "(nothing yet)"

    lines = [f"{item['id']}  {item['title']} — {item['teaser']}" for item in shelf]
    return (
        f"<memory>{memory}</memory>\n\n"
        f"<recent>{recent}</recent>\n\n"
        "<shelf>\n" + "\n".join(lines) + "\n</shelf>"
    )


def render_compress_context(journal, buffer) -> str:
    memory = journal["body"] if journal else "(nothing yet)"
    written = "\n\n---\n\n".join(p["body"] for p in buffer)
    return f"<memory>{memory}</memory>\n\n<written>{written}</written>"
