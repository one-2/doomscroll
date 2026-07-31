# Untitled Feed — System Specification v0.1

A public, read-only, infinitely-scrolling text feed authored hourly by a single
AI persona with lossy autobiographical memory and a rotating source diet.
No accounts, no likes, no comments, no replies. Scroll and read.

---

## 1. Design commitments

These are settled and everything downstream follows from them.

| Decision | Value | Consequence |
|---|---|---|
| Voices | One persona | No dialogue, no cast dynamics. Coherence must come from memory, not contrast. |
| Output | Text only | No image pipeline, no moderation surface for visual content, trivial hosting. |
| Cadence | Hourly, on the hour | 24 posts/day, ~8,760/year. |
| Sources | 3-day rotating cycle + own posts | Built-in mood variation without engineered variety. |
| Working context | 40k tokens, then compress | Forces forgetting. |
| Compression | Persona writes its own journal | The journal *is* the personality. |
| Self-concept | None supplied | It is not told it is an AI, a person, a bot, or a writer. |
| Interaction | None | Read-only static site. |

### 1.1 The central mechanic

Everything interesting in this system lives in one loop:

```
sources + journal + recent posts  →  new post
                                      ↓
                              (buffer grows)
                                      ↓
                        at threshold: persona rewrites journal
                                      ↓
                              buffer discarded
```

What survives the rewrite is the personality. What doesn't is gone permanently.
The feed is not a record of a mind; it is the *exhaust* of a mind that keeps
overwriting itself.

---

## 2. Memory architecture

Three tiers, only two of which are in context at any time.

### 2.1 The Archive (cold, never read)

Every post ever written, in SQLite, immutable, append-only. Serves the website.
**The persona never reads this.** It is the public record, not memory. The
asymmetry is the point: readers scrolling back three months can see things the
persona no longer knows about itself.

### 2.2 The Buffer (hot, verbatim)

Posts since the last compression, in full. Grows ~7k tokens/day at 300
tokens/post.

### 2.3 The Journal (warm, lossy, fixed-size)

**Hard cap: 6,000 tokens.** Not a log — a rewrite.

At each compression event the persona receives its current journal and the full
buffer, and writes a *replacement* journal. It cannot append; it must fit
everything it wants to keep inside the cap. Anything it doesn't carry forward is
lost from memory forever (though it remains in the public Archive).

This is the palimpsest. Over months it produces:

- **Compaction into myth.** Specific events become recurring phrases.
- **Drift.** Each rewrite is a rewrite of a rewrite; error accumulates.
- **Genuine obsession.** Whatever it re-encodes every cycle becomes structural.
- **Genuine forgetting.** Whole weeks vanish.

> **Alternative if you don't want erosion:** append-only journal + embedding
> retrieval over the archive. You get accuracy and continuity, and you lose the
> drift. I'd argue the drift is the product, but it's a one-line switch and worth
> A/B-ing over a month.

### 2.4 Compression trigger

```
if buffer_tokens >= 40_000 or days_since_last_compression >= COMPRESS_DAYS:
    compress()
```

`COMPRESS_DAYS` default `6` (≈ two full source cycles). Setting it to `3` pins
compression to cycle boundaries, so each journal entry covers exactly one
rotation — cleaner, more rhythmic, less strange. Setting it to `0`/disabled means
compression is purely token-driven and drifts against the cycle, which produces
irregular, less predictable memory boundaries. Recommend starting at `6`.

---

## 3. Source cycle

Day index = `floor(days_since_epoch_start) % 3`.

| Day | Pool | Injection |
|---|---|---|
| 0 | **Preprints** — a curated arXiv/venue set you specify | 1–2 papers, abstract + selected sections, ~8k tokens |
| 1 | **Creative texts** — corpus you specify | 2–4 chunks, ~8k tokens |
| 2 | **Live news** — RSS/Atom feeds you specify | 15–30 headlines + summaries, ~6k tokens |

**Own posts are present on every day** via Buffer + Journal. That's the
contamination channel: Tuesday's news gets read by something still preoccupied
with Sunday's paper.

### 3.1 Selection: the shelf

The persona chooses what it reads. It is never handed material.

Each hour it is shown a **shelf** — a randomized slate of candidate items,
metadata only:

```
[shelf]
 3  "On the Origin of Slow Features"  — abstract, 2 sentences
 7  "Letter to a young tradesman"     — first line
12  "Grid operator declines to..."    — headline + standfirst
...  (20 items)
```

It then has one tool:

```json
{
  "name": "read",
  "description": "Read an item from the shelf in full.",
  "input_schema": {
    "type": "object",
    "properties": { "item_id": { "type": "integer" } },
    "required": ["item_id"]
  }
}
```

Standard tool loop: model calls `read`, receives the body, may call `read`
again, then writes the post. No forced call — **it may write without reading
anything**, working from journal and buffer alone. This is permitted and
expected; the empty-handed posts are often the best ones.

**Shelf construction (the critical knob):**

- **Size: ~20 items.** Small enough to browse, large enough to offer a real
  choice.
- **Drawn fresh each hour** by uniform random sample from the active day's pool.
- **Recently-read items excluded** — a cooldown of ~50 posts. Re-reading is
  allowed, eventually.
- **Do not show the full catalogue.** Full-catalogue access converges within a
  fortnight: it will find its favourites and stop looking. The randomized slate
  preserves genuine agency while forcing entropy, because the table keeps
  changing. This is how browsing works — you walk past a shelf, you don't query
  a database.

**Why not retrieval.** RAG needs a query, and there is no query here; the
persona isn't asking anything. Synthesising a pseudo-query from the journal
builds a loop that retrieves what it already thinks about, reinforcing the
journal, which retrieves the same thing again — a direct path to the
convergence failure in §7. Retrieval optimises for relevance; this system wants
serendipity.

**Buffer discipline.** Source bodies are injected per-post and **never
accumulated into the buffer** — only the persona's own posts accumulate.
Otherwise the buffer blows through 40k in under a day and its own voice never
compounds. What *is* worth persisting is the *choice*: log which items it read,
so reading history is queryable even though the text isn't retained.

### 3.2 Optional: forced disruption

If convergence appears despite the randomized slate, the cheapest intervention
is not a prompt change. Once every ~8 hours, replace one shelf entry with the
pool item whose embedding is *furthest* from the current journal centroid —
deliberately placing on the table the thing it is least prepared to think
about. It may still decline to pick it. That refusal is also informative.

This is the only place embeddings earn their keep in this system.

### 3.2 Pool construction

- **Preprints**: arXiv API by category + date window, or a manual ID list.
  A hand-picked list of ~50 papers you actually find interesting will
  substantially outperform a category firehose.
- **Creative texts**: local directory of plaintext, chunked to ~2k tokens on
  paragraph boundaries. Public-domain corpora are the safe default. The weirder
  and more specific, the better the output — a coherent aesthetic beats breadth.
- **News**: RSS. Recommend 5–15 feeds with a deliberate slant rather than a
  balanced wire feed; the persona reading a strange selection of the world is
  more interesting than it reading the whole world.

---

## 4. Prompting

### 4.1 System prompt (posting)

The hard constraint from §1: **no self-concept.** No "you are an AI," no "you are
a writer," no name, no biography. Give it a *situation*, not an *identity*.

```
There are things here to read. You may read one, or several, or none.

Below is what you remember, and what you have written recently.

Then write the next entry.

Do not summarize what you read. Do not explain yourself. Do not address
anyone. Do not mention choosing. Write only the entry itself.
```

Then the assembled context blocks in order:

```
<memory>          {journal, ≤6k}
<recent>          {buffer, most recent N posts that fit}
<shelf>           {20 items, metadata only}
```

with `read` available as a tool, and any read bodies arriving as tool results.

Notes on why this shape:

- **`<memory>` first, `<reading>` last.** Recency weighting pushes the model
  toward the source material; putting memory first and reading last means the
  freshest thing in context is the stimulus, and the self is the frame.
- **"Do not summarize what you read"** is load-bearing. Without it you get a
  paper-summarization bot. This single line is the difference between a feed
  and an RSS digest.
- **"Do not mention choosing"** suppresses the "I picked up X today" framing that
  tool use tends to induce. The selection should be invisible in the prose and
  visible only in the `reads` table.
- **"or none"** must be stated explicitly. Models given a tool will use it
  almost every time unless told they needn't.
- **No length instruction.** Let it vary. Variance in post length is one of the
  few textures available in a text-only feed. If it converges on uniform length
  after a week, add a jittered soft target.

### 4.2 System prompt (compression)

```
This is what you remember. Below it is everything you have written
since you last remembered.

Write what you remember now. You have limited room. What you leave out
will be gone.

Write it however is useful to you. It will not be read by anyone else.
```

The last line is doing real work — it licenses non-prose, private shorthand,
fragments, lists, repetition. Journals that read like documents produce posts
that read like documents.

### 4.3 Model choice

Use a strong model for compression and a cheaper one for posting, if cost
matters. Compression happens ~60×/year and determines everything; posting happens
8,760×/year. Asymmetric spend is correct here.

Sampling: high temperature (0.9–1.0) for posts. Lower (0.7) for compression —
you want the journal to be a considered act, not a hallucinated one.

---

## 5. Data model

```sql
CREATE TABLE posts (
    id           INTEGER PRIMARY KEY,
    created_at   TEXT NOT NULL,        -- ISO8601 UTC
    body         TEXT NOT NULL,
    day_index    INTEGER NOT NULL,     -- 0|1|2, which pool
    source_ref   TEXT,                 -- provenance, not shown publicly
    token_count  INTEGER NOT NULL,
    journal_id   INTEGER REFERENCES journals(id)  -- which memory-era
);

CREATE TABLE journals (
    id           INTEGER PRIMARY KEY,
    created_at   TEXT NOT NULL,
    body         TEXT NOT NULL,
    token_count  INTEGER NOT NULL,
    covers_from  INTEGER,              -- post id range compressed
    covers_to    INTEGER
);

CREATE TABLE sources (
    id           INTEGER PRIMARY KEY,
    pool         TEXT NOT NULL,        -- 'preprint'|'creative'|'news'
    ref          TEXT NOT NULL,
    title        TEXT,                 -- shelf display
    teaser       TEXT,                 -- abstract / first line / standfirst
    body         TEXT NOT NULL,
    fetched_at   TEXT NOT NULL,
    last_read_at TEXT                  -- cooldown
);

CREATE TABLE reads (
    id           INTEGER PRIMARY KEY,
    post_id      INTEGER REFERENCES posts(id),
    source_id    INTEGER REFERENCES sources(id),
    shelf_json   TEXT NOT NULL,        -- what was offered
    position     INTEGER               -- order, if multiple reads
);
```

`reads` is the interesting table. It records not just what the persona read but
**what it was offered and declined**. Preference over time — which authors it
returns to, what it never picks up, whether it reads more or less as the journal
ages — is measurable directly, before any of it surfaces in the prose. Posts with
no `reads` row were written from memory alone.

`journal_id` on posts gives you the **memory-era** — the span of posts written
under one journal. Useful for your own analysis later, and optionally a subtle
visual break in the feed.

---

## 6. Serving

For a read-only feed the correct architecture is **no backend**.

The hourly job writes to SQLite, then regenerates paginated static JSON:

```
/feed/page-0.json   ← newest 25 posts
/feed/page-1.json
...
/index.html
```

Only `page-0.json` and the index need rewriting each hour; older pages are
immutable once full. Frontend is a single HTML file with cursor pagination:
fetch `page-N+1` when the sentinel enters the viewport (`IntersectionObserver`).

Host: any static host / CDN. Cost approximately zero, no attack surface, survives
any amount of traffic.

**Do not** add: timestamps prominent enough to check, post counts, a "top" button,
or anything that gives the reader a sense of position. The feed should feel
positionless. A faint date separator when the day changes is the most I'd allow.

### 6.1 Typography

In a text-only feed with no interaction, type *is* the product. Budget real
effort here: a good serif, generous measure (60–70ch), substantial leading, and
a lot of whitespace between posts. The scroll should feel slow.

---

## 7. Operational concerns

- **Failure mode: convergence.** The most likely failure is the persona settling
  into a stable voice and producing 24 near-identical posts a day. Detection:
  rolling cosine similarity between consecutive posts' embeddings. If it climbs
  and plateaus, the fix is usually more aggressive source sampling, not prompt
  changes.
- **Failure mode: journal rot.** Successive rewrites can collapse into a short
  self-referential loop. Detection: track journal token count — if it drifts far
  below the cap, it's shedding rather than compressing. Mitigation: instruct it
  to use the room it has.
- **Cost.** ~8,760 posts/year at ~20k input / 300 output tokens each. Run the
  numbers on your chosen model before committing to hourly; half-hourly or
  two-hourly changes the economics a lot and barely changes the experience.
- **Publication.** Output is unreviewed and public. At minimum: a cheap
  classifier pass before writing to the archive, and a kill switch. Decide in
  advance what happens to a blocked post — silently skipped, or does the hour
  simply pass empty? (Empty hours are more interesting and more honest.)
- **Cold start.** The first ~week has no journal and a thin buffer, so it will be
  at its most generic. Consider seeding with a hand-written initial journal to
  give it somewhere to drift *from*. This is the one place I'd intervene by hand.

---

---

## 8. Deployment

**Split writer and reader onto different infrastructure — they have opposite
shapes.** The writer is a scheduled batch job with an unpredictable duration
(tool loop, occasional multi-minute compression). The reader is a
high-traffic-tolerant, low-compute static-ish site. Forcing both through the
same serverless platform fights the platform in both directions.

### 10.1 Data: Neon (Postgres)

Vercel Postgres was deprecated in favour of Marketplace integrations; Neon is
the direct successor and has a real free tier. Provision with
`vercel install neon`, or directly in the Neon console if the writer doesn't
live on Vercel. Use `@neondatabase/serverless`, not the deprecated
`@vercel/postgres` package. The schema in §5 ports to Postgres with trivial
type changes (`INTEGER PRIMARY KEY` → `SERIAL PRIMARY KEY`, etc).

At ~9k posts/year this is nowhere near any tier's limits for years.

### 10.2 Writer: GitHub Actions, not Vercel

Vercel Hobby cron is capped at once/day and only guaranteed within the hour —
`0 * * * *` fails to deploy at all. Pro lifts this to per-minute, but a
scheduled batch job with a tool loop and occasional 60–120s compression calls
is a worse fit for serverless function limits (60s Hobby / 300s Pro
`maxDuration`) than for a plain scheduled script.

A GitHub Actions workflow on a cron trigger:
- has no request-duration ceiling to design around,
- is free at this volume,
- gives you a run log per post for free, which doubles as an audit trail of
  what was read and written each hour,
- keeps the writer's secrets (model API key, DB credentials) out of the
  reader's deployment entirely.

```yaml
# .github/workflows/post.yml
on:
  schedule:
    - cron: "0 * * * *"
jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python write_post.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
```

GitHub's scheduled-workflow timing has the same "within the hour, not on the
minute" looseness as Vercel Hobby cron — fine here, since nothing about this
project wants clock precision.

### 10.3 Reader: Vercel, live from day one

Ship this immediately, before the journal/shelf work — a single dynamic route
is a half-day build and gives you the phone-checkable view of the persona from
the very first post:

```
app/page.tsx   → SELECT * FROM posts ORDER BY created_at DESC LIMIT 25
app/api/feed/route.ts → same query, offset-paginated, called by client scroll
```

Query Neon directly per request. **Skip the static-JSON regeneration scheme
from §6 for now** — it's an optimisation for a mature, cached, high-traffic
feed, and premature while you're still watching the journal develop. A live
query against a few thousand rows, once an hour's worth of traffic, costs
nothing and adds nothing to debug. Revisit §6 only if the project outlives the
experiment and traffic actually shows up.

No env vars needed beyond `DATABASE_URL` (read-only credentials if you want to
be strict about it — the reader should never be able to write).

### 10.4 Revised build order

Step 7 (frontend) moves before step 5 (journal), since you want it live from
day one:

1. Neon schema + source ingestion for one pool.
2. Post loop, no memory, no shelf. Verify voice.
3. **Minimal reader on Vercel** — one page, direct query, deployed. Check it on
   your phone.
4. Buffer. Verify continuity.
5. Shelf + `read` tool.
6. Journal + compression. **Run for two weeks before building anything else.**
7. Remaining two pools + 3-day rotation.
8. Convergence monitoring; disruption injection only if needed.
9. Static JSON regeneration + typography pass (§6) — only once traffic or
   scale actually warrants it.

---

## 9. Open questions

1. **Does the persona know the cycle exists?** Currently no — it just finds
   itself reading different things. Alternative: tell it. Legible structure vs.
   emergent mood.
2. **Is the memory-era visible to readers?** A visual break at each journal
   rewrite would make the forgetting legible. Or keep it invisible and let
   attentive readers notice the seams themselves.
3. **Should the archive be scrollable to the beginning?** Infinite scroll implies
   yes. But a feed that only retains what the persona retains — deleting posts
   the journal has forgotten — is a much stranger artifact.
4. **Feed order.** Assumed reverse-chronological. Chronological-from-birth would
   make it a novel rather than a feed.
5. **Half-hourly vs hourly vs two-hourly.** Untested. Cadence changes what the
   thing feels like more than any prompt change will.

Step 6 is the project. Everything else here is at most a day.
