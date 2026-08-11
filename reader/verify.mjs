import { neon } from '@neondatabase/serverless';
import { readFileSync } from 'fs';
const sql = neon(readFileSync('/var/tmp/.dburl','utf8').trim());

const tables = await sql.query(
  "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1");
console.log('tables:', tables.map(r => r.tablename).join(', ') || '(none)');

const idx = await sql.query(
  "SELECT indexname FROM pg_indexes WHERE schemaname='public' ORDER BY 1");
console.log('indexes:', idx.map(r => r.indexname).join(', ') || '(none)');

const grants = await sql.query(`
  SELECT table_name, privilege_type FROM information_schema.role_table_grants
  WHERE grantee='reader_ro' ORDER BY 1,2`);
console.log('reader_ro grants:', grants.map(g => `${g.table_name}:${g.privilege_type}`).join(', ') || '(none)');

const counts = await sql.query(
  "SELECT (SELECT count(*) FROM posts) posts, (SELECT count(*) FROM sources) sources");
console.log('rows:', JSON.stringify(counts[0]));
