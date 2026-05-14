"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { fetchAnalysisJob, fetchAnalysisResult, fetchReplayArtifact, setDevUserId } from "@/lib/api";
import type { FakeAnalysisPayload, StructuredAIAnalysisPayload } from "@/lib/api";

const DEV_USER_ID = "00000000-0000-0000-0000-000000000001";

setDevUserId(DEV_USER_ID);

export default function AnalysisDetailPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const jobQuery = useQuery({
    queryKey: ["analysis-job", jobId],
    queryFn: () => fetchAnalysisJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 2000 : false;
    },
  });

  const resultQuery = useQuery({
    queryKey: ["analysis-result", jobId],
    queryFn: () => fetchAnalysisResult(jobId),
    enabled: jobQuery.data?.status === "succeeded",
  });

  const artifactQuery = useQuery({
    queryKey: ["replay-artifact", jobId],
    queryFn: () => fetchReplayArtifact(jobId),
    enabled: jobQuery.data?.status === "succeeded",
    retry: false,
  });

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto space-y-6">
      <Link href="/" className="text-sm text-indigo-300 hover:underline">
        ← Back to dashboard
      </Link>

      <header className="border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold text-slate-50">Analysis Status</h1>
        <p className="text-slate-500 mt-1">Job {jobId}</p>
      </header>

      {jobQuery.isLoading ? <Card title="Status">Loading...</Card> : null}
      {jobQuery.isError ? (
        <Card title="Status">
          <p className="text-red-400">Could not load analysis job.</p>
        </Card>
      ) : null}

      {jobQuery.data ? (
        <Card title="Status">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <StatusBadge status={jobQuery.data.status} />
              <span className="text-sm text-slate-400">{jobQuery.data.progress}%</span>
            </div>
            <ProgressBar progress={jobQuery.data.progress} />
            {jobQuery.data.error_message ? (
              <p className="text-sm text-red-400">{jobQuery.data.error_message}</p>
            ) : null}
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-slate-400">
              <Detail label="Upload" value={jobQuery.data.upload_id || "None"} />
              <Detail label="Queue Job" value={jobQuery.data.queue_job_id || "Not queued"} />
              <Detail label="Started" value={jobQuery.data.started_at || "Not started"} />
              <Detail label="Completed" value={jobQuery.data.completed_at || "Not completed"} />
            </dl>
          </div>
        </Card>
      ) : null}

      {resultQuery.isLoading ? <Card title="Result">Loading result...</Card> : null}
      {resultQuery.data ? <ResultCard result={resultQuery.data} /> : null}
      {artifactQuery.data ? <ReplayArtifactCard artifact={artifactQuery.data} /> : null}
      {jobQuery.data?.status === "succeeded" && resultQuery.isError ? (
        <Card title="Result">
          <p className="text-red-400">Could not load completed result.</p>
        </Card>
      ) : null}
    </main>
  );
}

function ResultCard({
  result,
}: {
  result: Awaited<ReturnType<typeof fetchAnalysisResult>>;
}) {
  if (result.result_kind === "structured_ai_analysis" && isStructuredAIAnalysisPayload(result.payload)) {
    return <StructuredAIResultCard result={result} payload={result.payload} />;
  }
  const payload = result.payload as FakeAnalysisPayload;

  return (
    <Card title="Fake Analysis Result">
      <div className="space-y-5">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">{result.title}</h2>
          <p className="text-slate-400 mt-1">{result.summary}</p>
          <p className="text-xs text-slate-600 mt-2">Schema: {result.schema_version}</p>
        </div>

        <ResultList title="Highlights" items={payload.highlights} />
        <ResultList title="Improvement Areas" items={payload.improvement_areas} />
        <ResultList title="Recommended Focus" items={payload.recommended_focus} />
        <ResultList title="Next Steps" items={payload.next_steps} />
      </div>
    </Card>
  );
}

function isStructuredAIAnalysisPayload(payload: unknown): payload is StructuredAIAnalysisPayload {
  return typeof payload === "object" && payload !== null && "schema_version" in payload && payload.schema_version === "coaching-analysis-v1";
}

function StructuredAIResultCard({
  result,
  payload,
}: {
  result: Awaited<ReturnType<typeof fetchAnalysisResult>>;
  payload: StructuredAIAnalysisPayload;
}) {
  return (
    <Card title="AI Coaching Analysis">
      <div className="space-y-5">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-semibold text-slate-100">{payload.title}</h2>
            <span className="text-xs uppercase tracking-wide text-indigo-300">{payload.confidence} confidence</span>
          </div>
          <p className="text-slate-400 mt-1">{payload.executive_summary}</p>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-slate-400 mt-3">
            <Detail label="Source Mode" value={payload.match_context.source_mode} />
            <Detail label="Match ID" value={payload.match_context.match_id ? String(payload.match_context.match_id) : "Unknown"} />
            <Detail label="Hero" value={payload.match_context.hero || "Unknown"} />
            <Detail label="Model" value={`${payload.model_metadata.provider} / ${payload.model_metadata.model}`} />
          </dl>
        </div>

        <CoachingPointList title="Strengths" items={payload.strengths} />
        <CoachingPointList title="Improvement Areas" items={payload.improvement_areas} />
        <KeyMomentList items={payload.key_moments} />
        <AdviceList title="Build Advice" items={payload.build_advice} />
        <AdviceList title="Priority Focus" items={payload.priority_focus} />
        <EvidenceList items={payload.evidence} />
        {payload.source_warnings.length > 0 ? (
          <ResultList title="Source Warnings" items={payload.source_warnings.map((warning) => warning.message)} />
        ) : null}
        <p className="text-xs text-slate-600">
          Schema: {result.schema_version} · Prompt: {payload.model_metadata.prompt_version} · Workflow: {payload.model_metadata.workflow_version}
        </p>
      </div>
    </Card>
  );
}

function CoachingPointList({
  title,
  items,
}: {
  title: string;
  items: Array<{ title: string; description: string; impact?: string; category?: string; evidence_refs?: string[] }>;
}) {
  if (items.length === 0) return null;
  return (
    <section>
      <h3 className="text-sm font-medium text-slate-300 mb-2">{title}</h3>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={`${title}-${item.title}`} className="rounded border border-slate-800 p-3 text-sm">
            <div className="flex flex-wrap gap-2 items-center">
              <h4 className="font-medium text-slate-200">{item.title}</h4>
              {item.impact ? <span className="text-xs text-indigo-300">{item.impact}</span> : null}
              {item.category ? <span className="text-xs text-slate-500">{item.category}</span> : null}
            </div>
            <p className="text-slate-400 mt-1">{item.description}</p>
            {item.evidence_refs && item.evidence_refs.length > 0 ? (
              <p className="text-xs text-slate-600 mt-1">Evidence: {item.evidence_refs.join(", ")}</p>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function KeyMomentList({ items }: { items: Array<{ title: string; description: string; timestamp_seconds?: number | null; impact?: string }> }) {
  if (items.length === 0) return null;
  return (
    <section>
      <h3 className="text-sm font-medium text-slate-300 mb-2">Key Moments</h3>
      <ul className="space-y-2 text-sm text-slate-400">
        {items.map((item) => (
          <li key={item.title} className="rounded border border-slate-800 p-3">
            <span className="font-medium text-slate-200">{item.title}</span>
            {item.timestamp_seconds !== undefined && item.timestamp_seconds !== null ? (
              <span className="text-xs text-slate-500 ml-2">{item.timestamp_seconds}s</span>
            ) : null}
            <p className="mt-1">{item.description}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AdviceList({ title, items }: { title: string; items: Array<{ title: string; description: string }> }) {
  if (items.length === 0) return null;
  return (
    <section>
      <h3 className="text-sm font-medium text-slate-300 mb-2">{title}</h3>
      <ul className="list-disc pl-5 space-y-1 text-sm text-slate-400">
        {items.map((item) => (
          <li key={`${title}-${item.title}`}>
            <span className="text-slate-200">{item.title}:</span> {item.description}
          </li>
        ))}
      </ul>
    </section>
  );
}

function EvidenceList({ items }: { items: Array<{ ref_id: string; source_type: string; description: string }> }) {
  if (items.length === 0) return null;
  return (
    <section>
      <h3 className="text-sm font-medium text-slate-300 mb-2">Evidence</h3>
      <ul className="space-y-1 text-sm text-slate-400">
        {items.map((item) => (
          <li key={item.ref_id}>
            <span className="text-slate-200">{item.ref_id}</span> ({item.source_type}): {item.description}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ReplayArtifactCard({
  artifact,
}: {
  artifact: Awaited<ReturnType<typeof fetchReplayArtifact>>;
}) {
  const parsed = artifact.artifact;
  const players = Array.isArray(parsed?.players) ? parsed.players.length : 0;
  const events = Array.isArray(parsed?.timeline) ? parsed.timeline.length : 0;
  const duration = parsed?.match?.duration_seconds;

  return (
    <Card title="Replay Parser Artifact">
      <div className="space-y-3 text-sm text-slate-400">
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <Detail label="Parser" value={`${artifact.parser_name}${artifact.parser_version ? ` ${artifact.parser_version}` : ""}`} />
          <Detail label="Schema" value={artifact.schema_version} />
          <Detail label="Duration" value={duration ? `${duration}s` : "Unavailable"} />
          <Detail label="Parse Time" value={artifact.parse_duration_ms ? `${artifact.parse_duration_ms}ms` : "Unavailable"} />
          <Detail label="Players" value={String(players)} />
          <Detail label="Timeline Events" value={String(events)} />
        </dl>
        {artifact.warnings.length > 0 ? (
          <ResultList title="Parser Warnings" items={artifact.warnings} />
        ) : null}
      </div>
    </Card>
  );
}

function ResultList({ title, items }: { title: string; items: unknown }) {
  const values = Array.isArray(items) ? items.map(String) : [];
  if (values.length === 0) {
    return null;
  }

  return (
    <section>
      <h3 className="text-sm font-medium text-slate-300 mb-2">{title}</h3>
      <ul className="list-disc pl-5 space-y-1 text-sm text-slate-400">
        {values.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="break-all">{value}</dd>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = status === "succeeded" ? "text-green-400" : status === "failed" ? "text-red-400" : "text-amber-300";
  return <span className={`text-xs uppercase tracking-wide ${color}`}>{status}</span>;
}

function ProgressBar({ progress }: { progress: number }) {
  return (
    <div className="h-2 rounded bg-slate-800 overflow-hidden">
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
