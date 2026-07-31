"""Prompts, verbatim. No persona name, no biography, no length instruction."""

SYSTEM_POST = """There are things here to read. You may read one, or several, or none.

Below is what you remember, and what you have written recently.

Then write the next entry.

Do not summarize what you read. Do not explain yourself. Do not address
anyone. Do not mention choosing. Write only the entry itself."""

SYSTEM_COMPRESS = """This is what you remember. Below it is everything you have written
since you last remembered.

Write what you remember now. You have limited room. What you leave out
will be gone.

Write it however is useful to you. It will not be read by anyone else."""

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
