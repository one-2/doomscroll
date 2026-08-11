-- The reader's role. Run after schema.sql, as the database owner.
--
-- Create the role with SQL, not with the Neon console or API. Neon grants
-- every role it creates membership in `neon_superuser`, which overrides the
-- grants below — such a role can read every table and write to all of them,
-- and the database owner cannot revoke it. A role created here has no
-- memberships. It does not appear in the console's role list, which is the
-- price of it actually being read-only.
--
-- Set a password of your own before using it.

CREATE ROLE reader_ro LOGIN PASSWORD 'replace-me';

GRANT CONNECT ON DATABASE neondb TO reader_ro;
GRANT USAGE ON SCHEMA public TO reader_ro;
GRANT SELECT ON posts TO reader_ro;

-- The reader shows the titles of what each post read. Columns, not tables:
-- sources.body is the corpus in full and the reader has no business with it.
GRANT SELECT (id, title) ON sources TO reader_ro;
GRANT SELECT (post_id, source_id, position) ON reads TO reader_ro;

-- Verify, connected as reader_ro. The first three must return; the rest fail.
--   SELECT id FROM posts LIMIT 1;
--   SELECT id, title FROM sources LIMIT 1;
--   SELECT post_id, source_id FROM reads LIMIT 1;
--   SELECT body FROM sources LIMIT 1;
--   SELECT shelf_json FROM reads LIMIT 1;
--   INSERT INTO posts (feed, body, token_count) VALUES ('mixed', 'x', 1);
