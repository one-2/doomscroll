"""Model access.

Requests go to OpenRouter, which speaks the Anthropic Messages API at
`/v1/messages`, so the tool loop and `cache_control` are unchanged from the
direct Anthropic client. Setting ANTHROPIC_API_KEY instead of
OPENROUTER_API_KEY talks to Anthropic directly.
"""

import logging
import os

from anthropic import Anthropic

from config import CACHE_PROMPT, OPENROUTER_BASE_URL, REFERER, TITLE

log = logging.getLogger(__name__)


def client() -> Anthropic:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("set OPENROUTER_API_KEY (or ANTHROPIC_API_KEY)")
        return Anthropic()

    # The SDK sends x-api-key whenever ANTHROPIC_API_KEY is set. OpenRouter
    # authenticates on the bearer token; sending both is rejected.
    os.environ.pop("ANTHROPIC_API_KEY", None)
    return Anthropic(
        base_url=OPENROUTER_BASE_URL,
        auth_token=key,
        default_headers={"HTTP-Referer": REFERER, "X-Title": TITLE},
    )


def caching() -> dict:
    """Top-level automatic caching: the breakpoint lands on the last cacheable
    block and advances as the conversation grows. Within one post's tool loop
    every call after the first re-sends the same prefix, which is where the
    saving is. Honoured by Anthropic directly and by OpenRouter."""
    return {"cache_control": {"type": "ephemeral"}} if CACHE_PROMPT else {}


def log_usage(label: str, response) -> None:
    u = getattr(response, "usage", None)
    if u is None:
        return
    log.info(
        "%s: in=%s out=%s cache_write=%s cache_read=%s",
        label,
        getattr(u, "input_tokens", "?"),
        getattr(u, "output_tokens", "?"),
        getattr(u, "cache_creation_input_tokens", 0),
        getattr(u, "cache_read_input_tokens", 0),
    )
