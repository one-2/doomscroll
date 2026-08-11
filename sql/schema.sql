-- Feed schema. Postgres (Neon).

CREATE TABLE journals (
    id           SERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    feed         TEXT NOT NULL,
    body         TEXT NOT NULL,
    token_count  INTEGER NOT NULL,
    covers_from  INTEGER,
    covers_to    INTEGER
);

CREATE TABLE posts (
    id           SERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    feed         TEXT NOT NULL,             -- nothing | news | creative | academic | mixed
    body         TEXT NOT NULL,
    day_index    SMALLINT,                   -- unused; the rotation is gone
    token_count  INTEGER NOT NULL,
    journal_id   INTEGER REFERENCES journals(id)
);
CREATE INDEX posts_created_idx ON posts (created_at DESC);
CREATE INDEX posts_feed_idx ON posts (feed, id DESC);
CREATE INDEX journals_feed_idx ON journals (feed, id DESC);

CREATE TABLE sources (
    id           SERIAL PRIMARY KEY,
    pool         TEXT NOT NULL CHECK (pool IN ('preprint','creative','news')),
    ref          TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL,
    teaser       TEXT NOT NULL,              -- abstract / first line / standfirst
    body         TEXT NOT NULL,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_read_at TIMESTAMPTZ
);
CREATE INDEX sources_pool_idx ON sources (pool, last_read_at);

CREATE TABLE reads (
    id           SERIAL PRIMARY KEY,
    post_id      INTEGER NOT NULL REFERENCES posts(id),
    source_id    INTEGER NOT NULL REFERENCES sources(id),
    shelf_json   JSONB NOT NULL,             -- full slate offered
    position     SMALLINT NOT NULL           -- 0-indexed read order
);
CREATE INDEX reads_source_idx ON reads (id DESC, source_id);
