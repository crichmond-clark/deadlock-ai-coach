# Auth Boundary Documentation

## Architecture

- **Next.js + Better Auth** owns browser authentication and session handling
- **FastAPI** validates signed auth tokens and resolves backend user records
- Clear separation: no duplication of auth ownership between frontend and backend

## Local Development

Local development bypasses OAuth entirely using the `X-Dev-User-Id` header:

```
X-Dev-User-Id: 00000000-0000-0000-0000-000000000001
```

This header is accepted by `resolve_current_user` in `apps/api/app/auth/dependencies.py` when `APP_ENV=local`. A dev user is auto-created or looked up by ID.

## Production Flow

1. User clicks "Sign in with Discord/GitHub" → Better Auth redirects to OAuth provider
2. OAuth provider returns authorization code → Better Auth exchanges for tokens
3. Better Auth creates session cookie in browser
4. Frontend calls FastAPI with `Authorization: Bearer <session_token>`
5. FastAPI validates JWT using `AUTH_SECRET` and extracts user identity
6. FastAPI looks up/creates backend User record via AuthIdentity table

## Environment Variables

```env
# Frontend (Next.js / Better Auth)
AUTH_SECRET=              # Generate with: openssl rand -hex 32
DISCORD_CLIENT_ID=        # From https://discord.com/developers/applications
DISCORD_CLIENT_SECRET=
GITHUB_CLIENT_ID=         # From https://github.com/settings/developers
GITHUB_CLIENT_SECRET=

# Backend (FastAPI)
AUTH_SECRET=             # Must match the value in Next.js
```

## Unresolved: Production Token Validation

The `resolve_current_user` dependency in `apps/api/app/auth/dependencies.py` currently raises 401 in production mode. Phase 1F defers implementing JWT/Better Auth token validation to avoid blocking Phase 1 completion.

**What needs to be implemented in Phase 1F (or later):**

1. FastAPI receives `Authorization: Bearer <token>` header
2. Validate the JWT using `AUTH_SECRET` (or Better Auth's public key)
3. Extract `provider` and `provider_subject` from token claims
4. Look up or create `AuthIdentity` record
5. Look up or create `User` record
6. Return the `User` object to the endpoint

**Options for token format:**

- **Option A**: Better Auth issues a signed JWT; FastAPI validates it using a shared secret or public key
- **Option B**: Better Auth stores session in Redis; FastAPI calls a Next.js endpoint to validate session
- **Option C**: Use Better Auth's session token format directly

Recommended: **Option A** — keeps backend stateless and avoids per-request calls to Next.js.

## Next Steps

- [ ] Implement token validation in `resolve_current_user`
- [ ] Test full OAuth flow with Discord and GitHub
- [ ] Add `AuthIdentity` creation when new OAuth users first sign in
- [ ] Verify JWT expiration and refresh handling