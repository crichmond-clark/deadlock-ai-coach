"use client";

import { useState } from "react";

import { authClient, useSession } from "@/auth/client";

export function SignInButton({ provider }: { provider: "discord" | "github" }) {
  const [error, setError] = useState<string | null>(null);
  const label = provider === "discord" ? "Discord" : "GitHub";

  async function handleSignIn() {
    setError(null);
    const result = await authClient.signIn.social({
      provider,
      callbackURL: "/",
    });

    if (result.error) {
      setError(result.error.message || `Could not start ${label} sign-in`);
    }
  }

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={handleSignIn}
        className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-sm"
      >
        Sign in with {label}
      </button>
      {error ? <p className="text-xs text-red-400 max-w-48">{error}</p> : null}
    </div>
  );
}

export function SignOutButton() {
  const [error, setError] = useState<string | null>(null);

  async function handleSignOut() {
    setError(null);
    const result = await authClient.signOut();

    if (result.error) {
      setError(result.error.message || "Could not sign out");
    }
  }

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={handleSignOut}
        className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-100 text-sm"
      >
        Sign out
      </button>
      {error ? <p className="text-xs text-red-400 max-w-48">{error}</p> : null}
    </div>
  );
}

export function AuthControls() {
  const session = useSession();

  if (session.isPending) {
    return <div className="text-sm text-slate-400">Checking session...</div>;
  }

  if (session.data) {
    return (
      <div className="flex items-center gap-3">
        <div className="text-right text-sm">
          <div className="text-slate-200">{session.data.user.name}</div>
          <div className="text-slate-500">{session.data.user.email}</div>
        </div>
        <SignOutButton />
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <SignInButton provider="discord" />
      <SignInButton provider="github" />
    </div>
  );
}
