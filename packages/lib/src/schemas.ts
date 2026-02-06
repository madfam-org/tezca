/**
 * Zod schemas for runtime validation of API responses.
 *
 * Each schema mirrors the corresponding TypeScript interface in types.ts.
 * Use `safeParseResponse` to validate API data at the boundary.
 */
import { z } from "zod";

// ── Law domain ──────────────────────────────────────────────────────────

export const LawVersionSchema = z.object({
    publication_date: z.string(),
    valid_from: z.string(),
    dof_url: z.string(),
    xml_file: z.string().nullable(),
});

export const LawSchema = z.object({
    id: z.string(),
    name: z.string(),
    short_name: z.string().optional(),
    fullName: z.string().optional(),
    category: z.string().optional(),
    tier: z.union([z.number(), z.string()]).optional(),
    versions: z.array(LawVersionSchema).optional(),
    articles: z.number().optional(),
    transitorios: z.number().optional(),
    grade: z.enum(["A", "B", "C", "D", "F"]).optional(),
    score: z.number().optional(),
    priority: z.number().optional(),
    file: z.string().optional(),
});

export const LawListItemSchema = z.object({
    id: z.string(),
    name: z.string(),
    versions: z.number(),
});

// ── Articles ────────────────────────────────────────────────────────────

export const LawArticleSchema = z.object({
    article_id: z.string(),
    text: z.string(),
});

export const LawArticleResponseSchema = z.object({
    law_id: z.string(),
    law_name: z.string(),
    total: z.number(),
    articles: z.array(LawArticleSchema),
});

// ── Search ──────────────────────────────────────────────────────────────

export const SearchResultSchema = z.object({
    id: z.string(),
    law_id: z.string(),
    law_name: z.string(),
    article: z.string(),
    snippet: z.string(),
    score: z.number(),
    date: z.string().optional(),
    municipality: z.string().optional(),
});

export const SearchResponseSchema = z.object({
    results: z.array(SearchResultSchema),
    total: z.number().optional(),
    page: z.number().optional(),
    page_size: z.number().optional(),
    total_pages: z.number().optional(),
    warning: z.string().optional(),
});

// ── Dashboard ───────────────────────────────────────────────────────────

export const RecentLawSchema = z.object({
    id: z.string(),
    name: z.string(),
    date: z.string(),
    tier: z.string(),
    category: z.string(),
});

export const DashboardStatsSchema = z.object({
    total_laws: z.number(),
    federal_count: z.number(),
    state_count: z.number(),
    municipal_count: z.number(),
    total_articles: z.number(),
    federal_coverage: z.number(),
    state_coverage: z.number(),
    municipal_coverage: z.number(),
    total_coverage: z.number(),
    last_update: z.string().nullable(),
    recent_laws: z.array(RecentLawSchema),
});

// ── Error ───────────────────────────────────────────────────────────────

export const APIErrorSchema = z.object({
    error: z.string(),
    details: z.string().optional(),
});

// ── Ingestion ───────────────────────────────────────────────────────────

export const IngestionResultsSchema = z.object({
    success_count: z.number(),
    total_laws: z.number(),
    duration_seconds: z.number().optional(),
});

export const IngestionStatusSchema = z.object({
    status: z.enum(["idle", "running", "completed", "failed", "error"]),
    message: z.string(),
    timestamp: z.string(),
    progress: z.number().optional(),
    params: z.record(z.string(), z.unknown()).optional(),
    results: IngestionResultsSchema.optional(),
    warning: z.string().optional(),
});

// ── Utility ─────────────────────────────────────────────────────────────

/**
 * Validate an API response against a Zod schema.
 * Returns the parsed data on success, or throws with a descriptive message.
 */
export function parseResponse<T>(schema: z.ZodType<T>, data: unknown): T {
    return schema.parse(data);
}

/**
 * Safely validate an API response without throwing.
 * Returns `{ success: true, data }` or `{ success: false, error }`.
 */
export function safeParseResponse<T>(
    schema: z.ZodType<T>,
    data: unknown,
): { success: true; data: T } | { success: false; error: z.ZodError } {
    const result = schema.safeParse(data);
    if (result.success) {
        return { success: true, data: result.data };
    }
    return { success: false, error: result.error };
}
