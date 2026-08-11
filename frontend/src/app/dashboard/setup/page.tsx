"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SetupRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center">
      <p className="text-gray-400">Opening OBSIDIAN dashboard...</p>
    </div>
  );
}
