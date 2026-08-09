"""Fill the source pools. Run on demand; idempotent on `ref`.

    python sources.py --pool news       hourly, alongside post.py
    python sources.py --pool preprint   one-off backfill from preprints.txt
    python sources.py --pool creative   one-off backfill from corpus/
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

import db
from config import ARXIV_API, ARXIV_DELAY, CHUNK_TOK, FETCH_TIMEOUT, approx_tokens

log = logging.getLogger(__name__)
HERE = Path(__file__).parent
CORPUS = HERE / "corpus"
FEEDS = HERE / "feeds.txt"
PREPRINTS = HERE / "preprints.txt"
UA = {"User-Agent": "feed/0.1 (source ingestion; contact via repository)"}


def _lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n")).strip()


def _sentences(text: str, n: int) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n]).strip()


def _fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=UA, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        log.warning("fetch failed %s: %s", url, exc)
        return None


# --- preprints -------------------------------------------------------------

def ingest_preprints(conn) -> int:
    ids = _lines(PREPRINTS)
    written = 0
    for arxiv_id in ids:
        time.sleep(ARXIV_DELAY)              # arXiv asks for 1 request / 3s
        raw = _fetch(f"{ARXIV_API}?id_list={arxiv_id}&max_results=1")
        if raw is None:
            continue
        entries = feedparser.parse(raw).entries
        if not entries:
            log.warning("no entry for %s", arxiv_id)
            continue
        entry = entries[0]
        title = " ".join(entry.title.split())
        abstract = " ".join(entry.summary.split())

        body = abstract
        full = _fetch(f"https://export.arxiv.org/html/{arxiv_id}")
        if full:
            body = f"{abstract}\n\n{_text(full)}"

        if db.upsert_source(conn, "preprint", f"arxiv:{arxiv_id}", title,
                            _sentences(abstract, 2), body):
            written += 1
    return written


# --- creative --------------------------------------------------------------

def chunk(text: str, budget: int = CHUNK_TOK) -> list[str]:
    """Split on paragraph boundaries into pieces of roughly `budget` tokens."""
    chunks, current, size = [], [], 0
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        cost = approx_tokens(para)
        if current and size + cost > budget:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(para)
        size += cost
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def ingest_creative(conn) -> int:
    written = 0
    for path in sorted(CORPUS.glob("*.txt")):
        pieces = chunk(path.read_text(encoding="utf-8", errors="replace"))
        for n, piece in enumerate(pieces, start=1):
            title = f"{path.name} §{n}"
            teaser = piece.strip().splitlines()[0][:300]
            if db.upsert_source(conn, "creative", f"corpus:{path.name}#{n}",
                                title, teaser, piece):
                written += 1
    return written


# --- news ------------------------------------------------------------------

def ingest_news(conn) -> int:
    written = 0
    for url in _lines(FEEDS):
        raw = _fetch(url)
        if raw is None:
            continue
        for entry in feedparser.parse(raw).entries:
            link = entry.get("link") or entry.get("id")
            if not link:
                continue
            title = " ".join(entry.get("title", "untitled").split())
            summary = _text(entry.get("summary", ""))[:2000]

            body = summary
            page = _fetch(link)
            if page:
                body = f"{summary}\n\n{_text(page)}" if summary else _text(page)
            if not body.strip():
                continue

            if db.upsert_source(conn, "news", link, title,
                                _sentences(summary, 2) or title, body):
                written += 1
    return written


POOLS = {
    "preprint": ingest_preprints,
    "creative": ingest_creative,
    "news": ingest_news,
}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", required=True, choices=sorted(POOLS))
    args = parser.parse_args()

    with db.connect() as conn:
        written = POOLS[args.pool](conn)
        conn.commit()
    log.info("%s: %d new source(s)", args.pool, written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
