"use client";

/**
 * Auth UI — skeleton placeholder for Phase 1F.
 * Real OAuth sign-in/sign-out will be implemented when Better Auth
 * v1.6.10 API is verified and configured in Phase 2.
 */

export function SignInButton({ provider }: { provider: "discord" | "github" }) {
  return (
    <button
      disabled
      className="px-4 py-2 rounded bg-slate-800 text-slate-400 cursor-not-allowed text-sm"
      title="OAuth setup deferred to Phase 2 — use X-Dev-User-Id for local dev"
    >
      Sign in with {provider === "discord" ? "Discord" : "GitHub"} (Phase 2)
    </button>
  );
}

export function SignOutButton() {
  return (
    <button
      disabled
      className="px-4 py-2 rounded bg-slate-800 text-slate-400 cursor-not-allowed text-sm"
      title="OAuth setup deferred to Phase 2"
    >
      Sign Out (Phase 2)
    </button>
  );
}