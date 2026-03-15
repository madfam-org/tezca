"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import posthog from "posthog-js";
import { initPostHog } from "@/lib/analytics/posthog";

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => { initPostHog(); }, []);

  useEffect(() => {
    if (posthog.__loaded) {
      posthog.capture("$pageview");
    }
  }, [pathname, searchParams]);

  return <>{children}</>;
}
