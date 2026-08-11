"""Postgres access. One connection per invocation."""

import os
import re
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


@contextmanager
def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    with psycopg.connect(url, row_factory=dict_row) as conn:
        yield conn


def latest_journal(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, created_at, body FROM journals ORDER BY id DESC LIMIT 1"
        )
        return cur.fetchone()


def buffer_posts(conn):
    """Posts not yet folded into a journal, oldest first."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, created_at, body, token_count FROM posts "
            "WHERE journal_id IS NULL ORDER BY created_at, id"
        )
        return cur.fetchall()


def insert_post(conn, body: str, day_index: int, token_count: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO posts (body, day_index, token_count, journal_id) "
            "VALUES (%s, %s, %s, NULL) RETURNING id",
            (body, day_index, token_count),
        )
        return cur.fetchone()["id"]


def insert_read(conn, post_id: int, source_id: int, shelf, position: int) -> None:
    from psycopg.types.json import Jsonb

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO reads (post_id, source_id, shelf_json, position) "
            "VALUES (%s, %s, %s, %s)",
            (post_id, source_id, Jsonb(shelf), position),
        )


def mark_read(conn, source_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE sources SET last_read_at = now() WHERE id = %s", (source_id,))


def source_body(conn, source_id: int):
    with conn.cursor() as cur:
        cur.execute("SELECT title, body FROM sources WHERE id = %s", (source_id,))
        return cur.fetchone()


# Postgres text fields reject NUL. PDF extraction produces them, and other C0
# controls are noise in prose, so they are stripped at the one boundary every
# pool passes through.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean(text: str) -> str:
    return _CONTROL.sub("", text)


def source_exists(conn, ref: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM sources WHERE ref = %s", (ref,))
        return cur.fetchone() is not None


def upsert_source(conn, pool: str, ref: str, title: str, teaser: str, body: str) -> bool:
    """Insert if `ref` is new. Returns True when a row was written."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO sources (pool, ref, title, teaser, body) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (ref) DO NOTHING RETURNING id",
            (pool, ref, clean(title), clean(teaser), clean(body)),
        )
        return cur.fetchone() is not None
