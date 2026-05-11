/**
 * Better Auth configuration — skeleton for Phase 1F.
 *
 * Better Auth v1.6.10 has a significantly different API from earlier versions.
 * This file creates a minimal placeholder structure and defers real OAuth
 * configuration to Phase 2 when we can properly test the API.
 *
 * Architecture (confirmed in auth-boundary.md):
 * - Next.js + Better Auth owns browser authentication and session handling
 * - FastAPI validates signed auth tokens and resolves backend user records
 *
 * Local development: X-Dev-User-Id header bypass (working, tested in Phase 1D)
 *
 * TODO (Phase 2):
 * - Verify Better Auth v1.6.10 API surface
 * - Configure Discord and GitHub OAuth adapters
 * - Set up session cookie handling for production
 * - Implement JWT token validation in FastAPI resolve_current_user
 */

export const authConfig = {
  // Social OAuth providers — configure when ready
  socialProviders: {} as Record<string, { clientId: string; clientSecret: string }>,

  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // 1 day
  },

  // Auth secret — must match FastAPI AUTH_SECRET for token validation
  secret: process.env.AUTH_SECRET || "local-dev-secret-change-in-production",
};