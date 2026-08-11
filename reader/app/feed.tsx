"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Post } from "@/lib/db";
import { dayOf, stamp } from "@/lib/time";
import { feedOf } from "@/lib/feeds";

export default function Feed({ slug, initial }: { slug: string; initial: Post[] }) {
  const [posts, setPosts] = useState(initial);
  const [done, setDone] = useState(initial.length === 0);
  const loading = useRef(false);
  const sentinel = useRef<HTMLDivElement>(null);

  const more = useCallback(async () => {
    if (loading.current || done) return;
    loading.current = true;
    try {
      const cursor = posts[posts.length - 1]?.id;
      const response = await fetch(`/api/feed?feed=${slug}&cursor=${cursor}`);
      if (!response.ok) return;
      const { posts: next } = (await response.json()) as { posts: Post[] };
      if (next.length === 0) setDone(true);
      else setPosts((current) => [...current, ...next]);
    } finally {
      loading.current = false;
    }
  }, [posts, done, slug]);

  useEffect(() => {
    const node = sentinel.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => entries[0].isIntersecting && more(),
      { rootMargin: "800px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [more]);

  let previousDay: string | null = null;

  const entry = feedOf(slug);

  return (
    <main>
      {entry && <p className="note">{entry.note}</p>}
      {posts.length === 0 && <p className="note">Nothing here yet.</p>}
      {posts.map((post) => {
        const day = dayOf(post.created_at);
        const separator = day !== previousDay;
        previousDay = day;
        return (
          <article key={post.id}>
            <div className="stamp">
              <time dateTime={post.created_at}>
                {stamp(post.created_at, separator)}
              </time>
              {post.reads?.length > 0 && (
                <span className="read"> read {post.reads.join(" · ")}</span>
              )}
            </div>
            {post.body.split(/\n\s*\n/).map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </article>
        );
      })}
      <div ref={sentinel} aria-hidden="true" />
    </main>
  );
}
