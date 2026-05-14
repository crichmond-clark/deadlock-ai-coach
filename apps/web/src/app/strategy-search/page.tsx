"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createKnowledgeSource,
  listKnowledgeSources,
  searchStrategyKnowledge,
  setDevUserId,
  type StrategySearchResult,
} from "@/lib/api";

const DEV_USER_ID = "00000000-0000-0000-0000-000000000001";

setDevUserId(DEV_USER_ID);

export default function StrategySearchPage() {
  return (
    <main className="min-h-screen p-8 max-w-5xl mx-auto space-y-8">
      <header className="border-b border-slate-800 pb-4 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-50">Strategy Search</h1>
          <p className="text-slate-400 mt-1">Ingest notes and retrieve citation-ready strategy context.</p>
        </div>
        <Link href="/" className="text-sm text-indigo-300 hover:text-indigo-200 underline">
          Home
        </Link>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <IngestSourceForm />
        <KnowledgeSourceList />
      </section>

      <SearchPanel />
    </main>
  );
}

function IngestSourceForm() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [patchVersion, setPatchVersion] = useState("");

  const mutation = useMutation({
    mutationFn: createKnowledgeSource,
    onSuccess: () => {
      setTitle("");
      setContent("");
      setTags("");
      setPatchVersion("");
      queryClient.invalidateQueries({ queryKey: ["knowledge-sources"] });
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate({
      title,
      source_type: "note",
      content,
      patch_version: patchVersion || null,
      tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
    });
  }

  return (
    <Card title="Add Strategy Note">
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextInput label="Title" value={title} onChange={setTitle} placeholder="Laning vs aggressive duo" />
        <TextInput label="Patch" value={patchVersion} onChange={setPatchVersion} placeholder="optional" />
        <TextInput label="Tags" value={tags} onChange={setTags} placeholder="laning, objectives" />
        <label className="block space-y-1">
          <span className="text-sm text-slate-300">Content</span>
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            rows={8}
            className="w-full rounded bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100"
            placeholder="Paste a guide, patch note excerpt, or coaching note..."
          />
        </label>
        <button
          type="submit"
          disabled={mutation.isPending || !title.trim() || !content.trim()}
          className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm"
        >
          {mutation.isPending ? "Ingesting..." : "Ingest note"}
        </button>
        {mutation.isError ? <p className="text-sm text-red-400">{mutation.error.message}</p> : null}
        {mutation.isSuccess ? <p className="text-sm text-green-400">Knowledge source ready.</p> : null}
      </form>
    </Card>
  );
}

function KnowledgeSourceList() {
  const sourcesQuery = useQuery({ queryKey: ["knowledge-sources"], queryFn: listKnowledgeSources });

  if (sourcesQuery.isLoading) {
    return <Card title="Knowledge Sources">Loading...</Card>;
  }
  if (sourcesQuery.isError) {
    return <Card title="Knowledge Sources"><span className="text-red-400">Could not load sources</span></Card>;
  }

  const sources = sourcesQuery.data?.sources ?? [];
  return (
    <Card title="Knowledge Sources">
      {sources.length === 0 ? (
        <p className="text-sm text-slate-500">No sources yet.</p>
      ) : (
        <ul className="space-y-3">
          {sources.map((source) => (
            <li key={source.id} className="border border-slate-800 rounded p-3">
              <div className="font-medium text-slate-100">{source.title}</div>
              <div className="text-xs text-slate-500">{source.status} · {source.chunk_count} chunks</div>
              <TagList tags={source.tags} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function SearchPanel() {
  const [query, setQuery] = useState("");
  const [tags, setTags] = useState("");
  const mutation = useMutation({ mutationFn: searchStrategyKnowledge });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate({
      query,
      top_k: 5,
      tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      include_global: true,
    });
  }

  return (
    <Card title="Search Strategy Knowledge">
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextInput label="Query" value={query} onChange={setQuery} placeholder="How should I recover after losing lane?" />
        <TextInput label="Filter tags" value={tags} onChange={setTags} placeholder="optional: laning" />
        <button
          type="submit"
          disabled={mutation.isPending || !query.trim()}
          className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm"
        >
          {mutation.isPending ? "Searching..." : "Search"}
        </button>
      </form>

      {mutation.isError ? <p className="text-sm text-red-400 mt-4">{mutation.error.message}</p> : null}
      {mutation.data ? <SearchResults results={mutation.data.results} warnings={mutation.data.warnings} /> : null}
    </Card>
  );
}

function SearchResults({ results, warnings }: { results: StrategySearchResult[]; warnings: string[] }) {
  return (
    <div className="mt-6 space-y-4">
      {warnings.map((warning) => <p key={warning} className="text-sm text-amber-300">{warning}</p>)}
      {results.map((result) => (
        <article key={result.chunk_id} className="border border-slate-800 rounded p-4 space-y-2">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-semibold text-slate-100">{result.citation_label}</h3>
              <p className="text-xs text-slate-500">Score {result.score.toFixed(3)}{result.patch_version ? ` · ${result.patch_version}` : ""}</p>
            </div>
            <TagList tags={result.tags} />
          </div>
          <p className="text-sm text-slate-300 whitespace-pre-wrap">{result.snippet}</p>
          {result.url ? <a className="text-xs text-indigo-300 underline" href={result.url}>{result.url}</a> : null}
        </article>
      ))}
    </div>
  );
}

function TextInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="block space-y-1">
      <span className="text-sm text-slate-300">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded bg-slate-950 border border-slate-700 px-3 py-2 text-slate-100"
      />
    </label>
  );
}

function TagList({ tags }: { tags: string[] }) {
  if (tags.length === 0) {
    return null;
  }
  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {tags.map((tag) => <span key={tag} className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">{tag}</span>)}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-5 shadow">
      <h2 className="text-lg font-semibold text-slate-100 mb-4">{title}</h2>
      {children}
    </section>
  );
}
