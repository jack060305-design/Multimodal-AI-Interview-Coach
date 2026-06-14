"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAccessToken } from "@/lib/auth";

/** Entry URL: send guests to login, signed-in users to practice. */
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    void (async () => {
      const token = await getAccessToken();
      router.replace(token ? "/practice" : "/login");
    })();
  }, [router]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center text-slate-500">
      Loading interview coach…
    </div>
  );
}
