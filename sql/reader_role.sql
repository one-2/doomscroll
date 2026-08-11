-- Privileges for the reader's role. Run after schema.sql.
-- The role itself is created in the Neon console or with
--   neonctl roles create --name reader_ro ...
--
-- SELECT on posts only: the reader has no business reading sources, reads,
-- or journals, and never writes anything.

GRANT CONNECT ON DATABASE neondb TO reader_ro;
GRANT USAGE ON SCHEMA public TO reader_ro;
GRANT SELECT ON posts TO reader_ro;
