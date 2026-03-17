/**
 * POST /api/v1/auth/login — proxy route so the @janua/ui SignIn component
 * (which calls ${apiUrl}/api/v1/auth/login) works with tezca admin's
 * existing login logic at /api/auth/login.
 *
 * Re-exports the same POST handler to avoid code duplication.
 */
export { POST } from "@/app/api/auth/login/route";
