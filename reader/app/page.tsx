import Feed from "./feed";
import { page } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function Home() {
  const posts = await page();
  return <Feed initial={posts} />;
}
