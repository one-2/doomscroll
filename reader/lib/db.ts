import { neon } from "@neondatabase/serverless";

// Resolved per request, not at module load: Next imports this module while
// collecting page configuration, so reading the environment at the top level
// turns a missing variable into a failed build rather than a failed request.
function connect() {
  const url = process.env.DATABASE_URL_RO ?? process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL_RO is not set");
  return neon(url);
}

export const PAGE_SIZE = 25;

export type Post = {
  id: number;
  created_at: string;
  body: string;
  /** Titles of what was read before writing, in the order read. Empty if nothing. */
  reads: string[];
};

// Formatted in SQL so the value is an ISO string on both the server and the
// client, and the day separator is computed from the same bytes in both.
const CREATED = `to_char(p.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at`;

// One row per post regardless of how many sources it read, so the aggregate is
// a correlated subquery rather than a join that would multiply the posts.
const READS = `COALESCE((SELECT array_agg(s.title ORDER BY r.position)
                         FROM reads r JOIN sources s ON s.id = r.source_id
                         WHERE r.post_id = p.id), '{}') AS reads`;

const COLS = `p.id, ${CREATED}, p.body, ${READS}`;

/** Newest first, for the RSS feed. */
export async function recent(feed: string, limit = 50): Promise<Post[]> {
  const sql = connect();
  const rows = await sql`SELECT ${sql.unsafe(COLS)} FROM posts p
                         WHERE p.feed = ${feed}
                         ORDER BY p.id DESC LIMIT ${limit}`;
  return rows as Post[];
}

/** Newest first. `cursor` is a post id; results are strictly older than it. */
export async function page(feed: string, cursor?: number): Promise<Post[]> {
  const sql = connect();
  const rows = cursor
    ? await sql`SELECT ${sql.unsafe(COLS)} FROM posts p
                WHERE p.feed = ${feed} AND p.id < ${cursor}
                ORDER BY p.id DESC LIMIT ${PAGE_SIZE}`
    : await sql`SELECT ${sql.unsafe(COLS)} FROM posts p
                WHERE p.feed = ${feed}
                ORDER BY p.id DESC LIMIT ${PAGE_SIZE}`;
  return rows as Post[];
}
