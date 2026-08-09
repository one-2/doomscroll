"""Configuration. Every constant is overridable by an environment variable
of the same name."""

import os
from datetime import date


def _str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


POST_MODEL = _str("POST_MODEL", "claude-sonnet-5")
COMPRESS_MODEL = _str("COMPRESS_MODEL", "claude-opus-5")
SAFETY_MODEL = _str("SAFETY_MODEL", "claude-haiku-4-5")

POST_TEMP = _float("POST_TEMP", 1.0)
COMPRESS_TEMP = _float("COMPRESS_TEMP", 0.7)

JOURNAL_MAX_TOK = _int("JOURNAL_MAX_TOK", 6_000)
BUFFER_MAX_TOK = _int("BUFFER_MAX_TOK", 40_000)
COMPRESS_DAYS = _int("COMPRESS_DAYS", 6)
SHELF_SIZE = _int("SHELF_SIZE", 20)
READ_COOLDOWN = _int("READ_COOLDOWN", 50)   # posts before an item may reappear

POST_MAX_TOK = _int("POST_MAX_TOK", 2_000)
MAX_READS = _int("MAX_READS", 3)            # reads per post, to bound cost

# Day 0 of the three-day source cycle.
EPOCH_START = date.fromisoformat(_str("EPOCH_START", "2026-01-01"))
POOLS = ("preprint", "creative", "news")

# The Claude 5 models reject temperature/top_p/top_k with a 400, and they think
# by default, which spends the same max_tokens budget as the prose. The two
# knobs below hold the deviations; POST_TEMP and COMPRESS_TEMP above are still
# sent when the model accepts them.
SEND_TEMPERATURE = _bool("SEND_TEMPERATURE", False)
POST_THINKING = _str("POST_THINKING", "disabled")       # disabled | adaptive
COMPRESS_THINKING = _str("COMPRESS_THINKING", "disabled")

SAFETY_ENABLED = _bool("SAFETY_ENABLED", True)
KILL_SWITCH = _bool("KILL_SWITCH", False)

# Source ingestion.
ARXIV_API = _str("ARXIV_API", "https://export.arxiv.org/api/query")
ARXIV_DELAY = _float("ARXIV_DELAY", 3.0)    # seconds between arXiv requests
CHUNK_TOK = _int("CHUNK_TOK", 2_000)        # creative chunk size
FETCH_TIMEOUT = _float("FETCH_TIMEOUT", 30.0)


def approx_tokens(text: str) -> int:
    """Four characters to the token. Precision is not needed for a threshold."""
    return len(text) // 4


def sampling(temp: float) -> dict:
    return {"temperature": temp} if SEND_TEMPERATURE else {}


def thinking(mode: str) -> dict:
    return {"thinking": {"type": mode}} if mode in ("disabled", "adaptive") else {}
