"use client";

import posthog from "posthog-js";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? "";
const POSTHOG_HOST =
  process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://analytics.madfam.io";

let initialized = false;

export function initPostHog(): void {
  if (initialized || typeof window === "undefined") return;
  if (!POSTHOG_KEY) return;
  if (navigator.doNotTrack === "1") return;

  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: true,
    autocapture: true,
    respect_dnt: true,
    persistence: "localStorage+cookie",
    secure_cookie: true,
    disable_session_recording: true,
  });
  initialized = true;
}

export function identifyUser(userId: string, traits?: Record<string, unknown>): void {
  if (!initialized) return;
  posthog.identify(userId, traits);
}

export function resetUser(): void {
  if (!initialized) return;
  posthog.reset();
}

export function trackEvent(event: string, properties?: Record<string, unknown>): void {
  if (!initialized) return;
  posthog.capture(event, properties);
}
