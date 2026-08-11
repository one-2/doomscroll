import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Feed",
  description: "A text feed.",
  alternates: {
    types: { "application/rss+xml": [{ url: "/feed.xml", title: "Feed" }] },
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}
        <footer>
          <a href="/feed.xml">RSS</a>
        </footer>
      </body>
    </html>
  );
}
