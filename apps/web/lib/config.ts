/**
 * Centralized configuration for the web app.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/**
 * Internal API URL for server-side rendering inside Docker.
 * Falls back to API_BASE_URL when not set (e.g. local dev outside Docker).
 */
export const INTERNAL_API_URL = process.env.INTERNAL_API_URL || API_BASE_URL;

/**
 * Monetization toggle. When false (default), tier gates show "coming soon"
 * interest-capture forms instead of checkout links.
 * Set NEXT_PUBLIC_MONETIZATION_ENABLED=true to enable full monetization.
 */
export const MONETIZATION_ENABLED = process.env.NEXT_PUBLIC_MONETIZATION_ENABLED === 'true';
