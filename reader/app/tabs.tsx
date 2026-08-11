"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { FEEDS, isFeed } from "@/lib/feeds";

export default function Tabs() {
  const path = usePathname();
  const current = path.split("/")[1] ?? "";

  return (
    <nav>
      <div className="tabs">
        {FEEDS.map((f) => (
          <Link key={f.slug} href={`/${f.slug}`}
                className={current === f.slug ? "on" : undefined}>
            {f.label}
          </Link>
        ))}
      </div>
      <div className="tabs">
        {isFeed(current) && <a href={`/${current}/feed.xml`}>RSS</a>}
        <Link href="/about" className={current === "about" ? "on" : undefined}>
          About
        </Link>
      </div>
    </nav>
  );
}
