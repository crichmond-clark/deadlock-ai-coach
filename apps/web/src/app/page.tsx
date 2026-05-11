"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchHealth, fetchMe, listUploads } from "@/lib/api";

const DEV_USER_ID = "00000000-0000-0000-0000-000000000001";

export default function HomePage() {
  return (
    <main className="min-h-screen p-8 max-w-5xl mx-auto space-y-8">
      <header className="border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold text-slate-50">Deadlock AI Coach</h1>
        <p className="text-slate-400 mt-1">AI-powered coaching and match analysis</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatusCard />
        <UserCard />
      </div>

      <UploadsSection />
    </main>
  );
}

function StatusCard() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30 * 1000,
  });

  if (healthQuery.isLoading) {
    return <Card title="Service Status">Loading...</Card>;
  }

  if (healthQuery.isError) {
    return (
      <Card title="Service Status">
        <span className="text-red-400">Offline</span>
      </Card>
    );
  }

  const data = healthQuery.data!;
  return (
    <Card title="Service Status">
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-green-400" />
          <span className="text-green-400">Online</span>
        </div>
        <div className="text-sm text-slate-400">
          <div>Service: {data.service}</div>
          <div>Version: {data.version}</div>
        </div>
      </div>
    </Card>
  );
}

function UserCard() {
  const userQuery = useQuery({
    queryKey: ["me"],
    queryFn: () => fetchMe(DEV_USER_ID),
    retry: false,
  });

  if (userQuery.isLoading) {
    return <Card title="Current User">Loading...</Card>;
  }

  if (userQuery.isError) {
    return (
      <Card title="Current User">
        <span className="text-red-400">Not authenticated</span>
        <p className="text-xs text-slate-500 mt-1">Set up Better Auth in Phase 1F</p>
      </Card>
    );
  }

  const user = userQuery.data!;
  return (
    <Card title="Current User">
      <div className="space-y-1">
        <div className="font-medium text-slate-200">{user.display_name}</div>
        <div className="text-sm text-slate-400">{user.email || "No email"}</div>
        <div className="text-xs text-slate-600 mt-2">ID: {user.id}</div>
      </div>
    </Card>
  );
}

function UploadsSection() {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-slate-200">Recent Uploads</h2>
      <div className="text-sm text-slate-500">No uploads yet — Phase 2 will add upload UI</div>
    </section>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
      <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide mb-3">{title}</h3>
      {children}
    </div>
  );
}