"""Fill the source pools. Run on demand; idempotent on `ref`.

    python sources.py --pool news       hourly, alongside post.py
    python sources.py --pool preprint   one-off backfill from preprints.txt
                                        and documents.tsv
    python sources.py --pool creative   one-off backfill from corpus/
"""

import argparse
import csv
import io
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

import db
from config import (ARXIV_API, ARXIV_DELAY, CHUNK_TOK, CREATIVE_DELAY,
                    CREATIVE_INDEX, FETCH_TIMEOUT, approx_tokens)

log = logging.getLogger(__name__)
HERE = Path(__file__).parent
CORPUS = HERE / "corpus"
FEEDS = HERE / "feeds.txt"
PREPRINTS = HERE / "preprints.txt"
DOCUMENTS = HERE / "documents.tsv"
UA = {"User-Agent": "feed/0.1 (source ingestion; contact via repository)"}


def _entries(path: Path) -> list[tuple[str, str]]:
    """Each line is a value with an optional trailing `# comment`, which the
    lists use to carry the source's title. Whole-line comments are ignored."""
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+#", line, maxsplit=1)
        out.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""))
    return out


def _lines(path: Path) -> list[str]:
    return [value for value, _ in _entries(path)]


def _text(html: str) -> str:
    """Readable text. Prefers the main content element when the page has one."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside",
                     "form", "noscript", "iframe", "svg"]):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup
    return re.sub(r"\n{3,}", "\n\n", root.get_text("\n")).strip()


def _description(html: str) -> str:
    """The page's own summary, which beats the first two sentences of chrome."""
    soup = BeautifulSoup(html, "html.parser")
    for name, key in (("description", "name"), ("og:description", "property"),
                      ("twitter:description", "name")):
        tag = soup.find("meta", attrs={key: name})
        if tag and tag.get("content", "").strip():
            return " ".join(tag["content"].split())
    return ""


def _unwrap(text: str) -> str:
    """PDF extraction often emits one word per line. Collapse every newline,
    then break again only where a sentence ended."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"(?<![.!?:])\n", " ", text)
    text = re.sub(r"\n+", "\n\n", text)
    return text.strip()


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
    written = ingest_documents(conn)
    for arxiv_id in ids:
        if db.source_exists(conn, f"arxiv:{arxiv_id}"):
            continue
        time.sleep(ARXIV_DELAY)              # arXiv asks for 1 request / 3s
        try:
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
            conn.commit()
        except Exception:
            log.exception("skipping arxiv:%s", arxiv_id)
            conn.rollback()
    log.info("preprint: %d source(s) after this run", written)
    return written


def _pdf_text(url: str) -> str | None:
    try:
        r = requests.get(url, headers=UA, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        pages = PdfReader(io.BytesIO(r.content)).pages
        return _unwrap("\n".join(p.extract_text() or "" for p in pages))
    except Exception as exc:
        log.warning("pdf failed %s: %s", url, exc)
        return None


def ingest_documents(conn) -> int:
    """Papers and reports that are not on arXiv. Same pool as the preprints.

    A TSV of url, title, teaser. The teaser is supplied rather than scraped:
    a page's own summary is usually boilerplate about the publisher, and the
    teaser is the only thing the shelf shows.
    """
    if not DOCUMENTS.exists():
        return 0
    written = 0
    with DOCUMENTS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            url = (row.get("url") or "").strip()
            if not url or url.startswith("#"):
                continue
            if db.source_exists(conn, url):
                continue
            try:
                if url.lower().endswith(".pdf"):
                    body = _pdf_text(url)
                else:
                    page = _fetch(url)
                    body = _text(page) if page else None
                if not body:
                    continue
                title = (row.get("title") or "").strip() or url
                teaser = (row.get("teaser") or "").strip() or _sentences(body, 2)
                if db.upsert_source(conn, "preprint", url, title, teaser[:500], body):
                    written += 1
                conn.commit()
            except Exception:
                log.exception("skipping %s", url)
                conn.rollback()
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


def _index_links(index_url: str) -> list[tuple[str, str]]:
    """Documents linked from one index page. One level, no recursion."""
    page = _fetch(index_url)
    if page is None:
        return []
    soup = BeautifulSoup(page, "html.parser")
    base = index_url.rsplit("/", 1)[0] + "/"
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        url = urljoin(base, a["href"]).split("#")[0]
        if url in seen or url == index_url:
            continue
        if not url.startswith(base):     # stay in the index's own directory
            continue
        if not url.lower().endswith((".html", ".htm", ".pdf")):
            continue
        seen.add(url)
        out.append((" ".join(a.get_text(" ", strip=True).split()), url))
    return out


def _store_chunks(conn, ref: str, title: str, text: str) -> int:
    written = 0
    for n, piece in enumerate(chunk(text), start=1):
        teaser = " ".join(piece.split())[:300]
        if db.upsert_source(conn, "creative", f"{ref}#{n}",
                            f"{title} §{n}", teaser, piece):
            written += 1
    return written


def ingest_creative(conn, limit: int | None = None) -> int:
    """Local files in corpus/, then the documents linked from CREATIVE_INDEX.

    One request every CREATIVE_DELAY seconds, sequentially, one level deep.
    A document already stored is not fetched again.
    """
    written = 0
    for path in sorted(CORPUS.glob("*.txt")):
        written += _store_chunks(conn, f"corpus:{path.name}", path.name,
                                 path.read_text(encoding="utf-8", errors="replace"))

    links = _index_links(CREATIVE_INDEX)
    log.info("%d documents linked from %s", len(links), CREATIVE_INDEX)
    if limit is not None:
        links = links[:limit]

    for n, (title, url) in enumerate(links, start=1):
        if db.source_exists(conn, f"{url}#1"):
            continue
        time.sleep(CREATIVE_DELAY)
        try:
            if url.lower().endswith(".pdf"):
                text = _pdf_text(url)
            else:
                page = _fetch(url)
                text = _text(page) if page else None
            if not text or approx_tokens(text) < 100:
                continue
            written += _store_chunks(conn, url, title or url.rsplit("/", 1)[-1], text)
            conn.commit()          # per document, so a failure resumes exactly
        except Exception:
            # 312 documents from one archive vary more than any guard predicts.
            # One bad file must not end the run.
            log.exception("skipping %s", url)
            conn.rollback()
        if n % 25 == 0:
            log.info("  %d/%d documents, %d chunks", n, len(links), written)
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
            if not link or db.source_exists(conn, link):
                continue          # already stored; do not fetch the page again
            try:
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
                conn.commit()
            except Exception:
                log.exception("skipping %s", link)
                conn.rollback()
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
    parser.add_argument("--limit", type=int, default=None,
                        help="stop after this many documents (creative only)")
    args = parser.parse_args()

    with db.connect() as conn:
        if args.pool == "creative":
            written = ingest_creative(conn, limit=args.limit)
        else:
            written = POOLS[args.pool](conn)
        conn.commit()
    log.info("%s: %d new source(s)", args.pool, written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
