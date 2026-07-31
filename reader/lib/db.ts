import { neon } from "@neondatabase/serverless";

const url = process.env.DATABASE_URL_RO ?? process.env.DATABASE_URL;
if (!url) throw new Error("DATABASE_URL_RO is not set");

const sql = neon(url);

export const PAGE_SIZE = 25;

export type Post = {
  id: number;
  created_at: string;
  body: string;
};

// Formatted in SQL so the value is an ISO string on both the server and the
// client, and the day separator is computed from the same bytes in both.
const CREATED = `to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at`;

/** Newest first. `cursor` is a post id; results are strictly older than it. */
export async function page(cursor?: number): Promise<Post[]> {
  const rows = cursor
    ? await sql`SELECT id, ${sql.unsafe(CREATED)}, body FROM posts
                WHERE id < ${cursor} ORDER BY id DESC LIMIT ${PAGE_SIZE}`
    : await sql`SELECT id, ${sql.unsafe(CREATED)}, body FROM posts
                ORDER BY id DESC LIMIT ${PAGE_SIZE}`;
  return rows as Post[];
}
