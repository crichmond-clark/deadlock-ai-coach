"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AuthControls } from "@/auth/ui";
import {
  createAnalysisJob,
  createUpload,
  fetchHealth,
  fetchMe,
  listAnalysisJobs,
  listUploads,
  setDevUserId,
  type AnalysisJobResponse,
  type UploadCreateRequest,
} from "@/lib/api";

const DEV_USER_ID = "00000000-0000-0000-0000-000000000001";

setDevUserId(DEV_USER_ID);

export default function HomePage() {
  return (
    <main className="min-h-screen p-8 max-w-5xl mx-auto space-y-8">
      <header className="border-b border-slate-800 pb-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-50">Deadlock AI Coach</h1>
            <p className="text-slate-400 mt-1">AI-powered coaching and match analysis</p>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/strategy-search" className="text-sm text-indigo-300 hover:text-indigo-200 underline">
              Strategy Search
            </Link>
            <AuthControls />
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatusCard />
        <UserCard />
      </div>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <UploadForm />
        <UploadList />
      </section>

      <AnalysisHistory />
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
    queryFn: fetchMe,
    retry: false,
  });

  if (userQuery.isLoading) {
    return <Card title="Current User">Loading...</Card>;
  }

  if (userQuery.isError) {
    return (
      <Card title="Current User">
        <span className="text-red-400">Not authenticated</span>
        <p className="text-xs text-slate-500 mt-1">Use Better Auth or local dev auth.</p>
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

function UploadForm() {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState("replay");
  const [filename, setFilename] = useState("");
  const [sizeBytes, setSizeBytes] = useState("");
  const [summaryText, setSummaryText] = useState("");
  const [createdJob, setCreatedJob] = useState<AnalysisJobResponse | null>(null);

  const mutation = useMutation({
    mutationFn: async (payload: UploadCreateRequest) => {
      const upload = await createUpload(payload);
      return createAnalysisJob(upload.id);
    },
    onSuccess: (job) => {
      setFilename("");
      setSizeBytes("");
      setSummaryText("");
      setCreatedJob(job);
      queryClient.invalidateQueries({ queryKey: ["uploads"] });
      queryClient.invalidateQueries({ queryKey: ["analysis-jobs"] });
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const payload: UploadCreateRequest = {
      kind,
      filename: filename || null,
      size_bytes: sizeBytes ? Number(sizeBytes) : null,
      summary_text: summaryText || null,
    };

    mutation.mutate(payload);
  }

  return (
    <Card title="Start Fake Analysis">
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block space-y-1">
          <span className="text-sm text-slate-300">Kind</span>
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value)}
            className="w-full rounded bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100"
          >
            <option value="replay">Replay</option>
            <option value="screenshot">Screenshot</option>
            <option value="match_summary">Match summary</option>
          </select>
        </label>

        <label className="block space-y-1">
          <span className="text-sm text-slate-300">Filename</span>
          <input
            value={filename}
            onChange={(event) => setFilename(event.target.value)}
            placeholder="match.dem"
            className="w-full rounded bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm text-slate-300">Size bytes</span>
          <input
            value={sizeBytes}
            onChange={(event) => setSizeBytes(event.target.value)}
            type="number"
            min="0"
            placeholder="12345"
            className="w-full rounded bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm text-slate-300">Summary text</span>
          <textarea
            value={summaryText}
            onChange={(event) => setSummaryText(event.target.value)}
            rows={4}
            placeholder="Required for match summaries"
            className="w-full rounded bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100"
          />
        </label>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm"
        >
          {mutation.isPending ? "Enqueuing..." : "Create upload + analysis"}
        </button>

        {mutation.isError ? (
          <p className="text-sm text-red-400">{mutation.error.message}</p>
        ) : null}
        {createdJob ? (
          <p className="text-sm text-green-400">
            Analysis queued. {" "}
            <Link className="underline" href={`/analyses/${createdJob.id}`}>
              View status
            </Link>
          </p>
        ) : null}
      </form>
    </Card>
  );
}

function UploadList() {
  const uploadsQuery = useQuery({
    queryKey: ["uploads"],
    queryFn: listUploads,
  });

  if (uploadsQuery.isLoading) {
    return <Card title="Recent Uploads">Loading...</Card>;
  }

  if (uploadsQuery.isError) {
    return (
      <Card title="Recent Uploads">
        <span className="text-red-400">Could not load uploads</span>
      </Card>
    );
  }

  const uploads = uploadsQuery.data!.uploads;

  return (
    <Card title="Recent Uploads">
      {uploads.length === 0 ? (
        <p className="text-sm text-slate-500">No uploads yet.</p>
      ) : (
        <ul className="space-y-3">
          {uploads.map((upload) => (
            <li key={upload.id} className="border border-slate-800 rounded p-3">
              <div className="flex justify-between gap-3">
                <div>
                  <div className="font-medium text-slate-200">{upload.filename || upload.kind}</div>
                  <div className="text-xs text-slate-500">{upload.id}</div>
                </div>
                <span className="text-xs text-slate-400">{upload.status}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function AnalysisHistory() {
  const jobsQuery = useQuery({
    queryKey: ["analysis-jobs"],
    queryFn: listAnalysisJobs,
    refetchInterval: (query) => {
      const jobs = query.state.data?.jobs ?? [];
      return jobs.some((job) => job.status === "queued" || job.status === "running") ? 2000 : false;
    },
  });

  if (jobsQuery.isLoading) {
    return <Card title="Analysis History">Loading...</Card>;
  }

  if (jobsQuery.isError) {
    return (
      <Card title="Analysis History">
        <span className="text-red-400">Could not load analysis jobs</span>
      </Card>
    );
  }

  const jobs = jobsQuery.data!.jobs;

  return (
    <Card title="Analysis History">
      {jobs.length === 0 ? (
        <p className="text-sm text-slate-500">No analyses yet.</p>
      ) : (
        <ul className="space-y-3">
          {jobs.map((job) => (
            <li key={job.id} className="border border-slate-800 rounded p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <Link href={`/analyses/${job.id}`} className="font-medium text-indigo-300 hover:underline">
                    {job.result?.title || `Analysis ${job.id.slice(0, 8)}`}
                  </Link>
                  <div className="text-xs text-slate-500 mt-1">{job.id}</div>
                </div>
                <StatusBadge status={job.status} />
              </div>
              <ProgressBar progress={job.progress} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = status === "succeeded" ? "text-green-400" : status === "failed" ? "text-red-400" : "text-amber-300";
  return <span className={`text-xs uppercase tracking-wide ${color}`}>{status}</span>;
}

function ProgressBar({ progress }: { progress: number }) {
  return (
    <div className="mt-3 h-2 rounded bg-slate-800 overflow-hidden">
      <div className="h-full bg-indigo-500" style={{ width: `${progress}%` }} />
    </div>
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
