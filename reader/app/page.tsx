import { redirect } from "next/navigation";
import { DEFAULT_FEED } from "@/lib/feeds";

export default function Home() {
  redirect(`/${DEFAULT_FEED}`);
}
