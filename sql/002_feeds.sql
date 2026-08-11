-- Five feeds, each with its own memory. Run once against an existing database.
--
-- Existing rows are assigned to 'mixed': the original feed rotated across all
-- three pools, which is closer to mixed than to any single-pool feed.

ALTER TABLE posts    ADD COLUMN IF NOT EXISTS feed TEXT NOT NULL DEFAULT 'mixed';
ALTER TABLE journals ADD COLUMN IF NOT EXISTS feed TEXT NOT NULL DEFAULT 'mixed';

-- The three-day rotation is gone; each feed now has a fixed diet.
ALTER TABLE posts ALTER COLUMN day_index DROP NOT NULL;

CREATE INDEX IF NOT EXISTS posts_feed_idx    ON posts    (feed, id DESC);
CREATE INDEX IF NOT EXISTS journals_feed_idx ON journals (feed, id DESC);
