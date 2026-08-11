"""Configuration. Every constant is overridable by an environment variable
of the same name."""

import os


def _str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


# OpenRouter model ids. Talking to Anthropic directly instead needs the bare
# ids (claude-sonnet-5, claude-opus-5, claude-haiku-4-5).
POST_MODEL = _str("POST_MODEL", "anthropic/claude-sonnet-5")
COMPRESS_MODEL = _str("COMPRESS_MODEL", "anthropic/claude-opus-5")
SAFETY_MODEL = _str("SAFETY_MODEL", "anthropic/claude-haiku-4.5")

OPENROUTER_BASE_URL = _str("OPENROUTER_BASE_URL", "https://openrouter.ai/api")
REFERER = _str("REFERER", "https://github.com/one-2/doomscroll")
TITLE = _str("TITLE", "feed")

# Repeats the whole prefix on every tool-loop call at a tenth of the price.
CACHE_PROMPT = _bool("CACHE_PROMPT", True)

POST_TEMP = _float("POST_TEMP", 1.0)
COMPRESS_TEMP = _float("COMPRESS_TEMP", 0.7)

JOURNAL_MAX_TOK = _int("JOURNAL_MAX_TOK", 6_000)
BUFFER_MAX_TOK = _int("BUFFER_MAX_TOK", 40_000)
COMPRESS_DAYS = _int("COMPRESS_DAYS", 6)   # 0 disables the time trigger
SHELF_SIZE = _int("SHELF_SIZE", 20)
READ_COOLDOWN = _int("READ_COOLDOWN", 50)   # posts before an item may reappear

# The posting window, in local hours, inclusive at both ends. GitHub cron is
# UTC only and cannot follow AEST/AEDT, so the workflow fires on the union of
# both offsets and this drops the runs that fall outside the local window.
# Empty disables the check, which is what a manual dispatch wants.
POST_HOURS = _str("POST_HOURS", "8-12")
ZONE = _str("ZONE", "Australia/Sydney")

POST_MAX_TOK = _int("POST_MAX_TOK", 2_000)
MAX_READS = _int("MAX_READS", 3)            # reads per post, to bound cost

# Five feeds, each with its own journal, buffer and diet. The key is the
# database value and the URL slug; the value is the pools its shelf is drawn
# from. An empty tuple means no shelf at all.
FEEDS = {
    "nothing":  (),
    "news":     ("news",),
    "creative": ("creative",),
    "academic": ("preprint",),
    "mixed":    ("preprint", "creative", "news"),
}
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
# The creative pool is filled from an index page plus anything in corpus/.
CREATIVE_INDEX = _str("CREATIVE_INDEX", "https://www.ubu.com/papers/index.html")
CREATIVE_DELAY = _float("CREATIVE_DELAY", 2.0)   # seconds between documents
FETCH_TIMEOUT = _float("FETCH_TIMEOUT", 30.0)


def approx_tokens(text: str) -> int:
    """Four characters to the token. Precision is not needed for a threshold."""
    return len(text) // 4


def sampling(temp: float) -> dict:
    return {"temperature": temp} if SEND_TEMPERATURE else {}


def thinking(mode: str) -> dict:
    return {"thinking": {"type": mode}} if mode in ("disabled", "adaptive") else {}


def in_window(now=None) -> bool:
    """True if the local hour is inside POST_HOURS, or the check is off."""
    if not POST_HOURS.strip():
        return True
    first, _, last = POST_HOURS.partition("-")
    first, last = int(first), int(last or first)
    from datetime import datetime
    from zoneinfo import ZoneInfo

    hour = (now or datetime.now(ZoneInfo(ZONE))).astimezone(ZoneInfo(ZONE)).hour
    return first <= hour <= last
