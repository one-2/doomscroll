import type { Metadata } from "next";
import "./globals.css";
import Tabs from "./tabs";

export const metadata: Metadata = {
  title: "Feed",
  description: "A text feed.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Tabs />
        {children}
      </body>
    </html>
  );
}
