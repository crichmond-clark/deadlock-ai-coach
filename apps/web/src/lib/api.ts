const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// =============================================================================
// Dev Auth Bypass — Phase 1 only, replaced by Better Auth tokens in Phase 2
// =============================================================================
let _devUserId: string | undefined;

/** Set the dev user ID for all subsequent API calls (local development only). */
export function setDevUserId(id: string): void {
    _devUserId = id;
}

/** Clear the dev user ID. */
export function clearDevUserId(): void {
    _devUserId = undefined;
}

// =============================================================================
// Internal request helper
// =============================================================================

interface RequestOptions extends RequestInit {
    params?: Record<string, string | number | undefined>;
}

async function request<T>(
    path: string,
    options: RequestOptions = {},
): Promise<T> {
    const url = new URL(path, API_BASE);

    if (options.params) {
        Object.entries(options.params).forEach(([key, value]) => {
            if (value !== undefined) {
                url.searchParams.set(key, String(value));
            }
        });
    }

    const headers = new Headers({
        "Content-Type": "application/json",
        ...((options.headers as Record<string, string>) || {}),
    });

    // Dev auth bypass — attach X-Dev-User-Id header if set
    if (_devUserId) {
        headers.set("X-Dev-User-Id", _devUserId);
    }

    const response = await fetch(url.toString(), {
        ...options,
        headers,
    });

    if (!response.ok) {
        const error = await response
            .json()
            .catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `Request failed: ${response.status}`);
    }

    return response.json();
}

// =============================================================================
// Health
// =============================================================================

export async function fetchHealth() {
    return request<{ status: string; service: string; version: string }>(
        "/api/v1/health",
    );
}

export async function fetchReadiness() {
    return request<{ status: string; database: string; redis: string }>(
        "/api/v1/ready",
    );
}

// =============================================================================
// Auth / User
// =============================================================================

export async function fetchMe() {
    return request<{
        id: string;
        email: string | null;
        display_name: string | null;
        avatar_url: string | null;
    }>("/api/v1/me");
}

// =============================================================================
// Uploads
// =============================================================================

export interface UploadResponse {
    id: string;
    kind: string;
    status: string;
    filename: string | null;
    created_at: string;
}

export interface UploadCreateRequest {
    kind: string;
    filename?: string | null;
    content_type?: string | null;
    size_bytes?: number | null;
    storage_key?: string | null;
    summary_text?: string | null;
}

export async function createUpload(data: UploadCreateRequest) {
    return request<UploadResponse>("/api/v1/uploads", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function listUploads() {
    return request<{ uploads: UploadResponse[]; total: number }>(
        "/api/v1/uploads",
    );
}

// =============================================================================
// Analysis jobs
// =============================================================================

export interface AnalysisResultSummary {
    id: string;
    title: string;
    summary: string;
    schema_version: string;
}

export interface AnalysisJobResponse {
    id: string;
    upload_id: string | null;
    status: string;
    progress: number;
    queue_job_id: string | null;
    error_message: string | null;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    result: AnalysisResultSummary | null;
}

export interface ReplayParseArtifactResponse {
    id: string;
    job_id: string | null;
    upload_id: string;
    parser_name: string;
    parser_version: string | null;
    schema_version: string;
    status: string;
    artifact: {
        stats?: Record<string, unknown>;
        match?: Record<string, unknown>;
        players?: unknown[];
        timeline?: unknown[];
        [key: string]: unknown;
    } | null;
    warnings: string[];
    error_message: string | null;
    parse_duration_ms: number | null;
    created_at: string;
}

export interface StructuredCoachingPoint {
    title: string;
    description: string;
    impact?: string;
    category?: string;
    evidence_refs?: string[];
}

export interface StructuredKeyMoment {
    title: string;
    description: string;
    timestamp_seconds?: number | null;
    impact?: string;
    evidence_refs?: string[];
}

export interface StructuredBuildAdvice {
    title: string;
    description: string;
    item_name?: string | null;
    evidence_refs?: string[];
}

export interface StructuredPracticeFocus {
    title: string;
    description: string;
    timebox_minutes?: number | null;
    evidence_refs?: string[];
}

export interface StructuredSourceEvidence {
    ref_id: string;
    source_type: string;
    description: string;
    data_path?: string | null;
}

export interface StructuredAIAnalysisPayload {
    schema_version: "coaching-analysis-v1";
    title: string;
    executive_summary: string;
    confidence: "low" | "medium" | "high";
    match_context: {
        hero?: string | null;
        match_id?: number | null;
        source_mode: string;
        duration_seconds?: number | null;
        summary: string;
    };
    strengths: StructuredCoachingPoint[];
    improvement_areas: StructuredCoachingPoint[];
    key_moments: StructuredKeyMoment[];
    build_advice: StructuredBuildAdvice[];
    priority_focus: StructuredPracticeFocus[];
    evidence: StructuredSourceEvidence[];
    source_warnings: Array<{ source: string; code: string; message: string }>;
    model_metadata: {
        provider: string;
        model: string;
        prompt_version: string;
        workflow_version: string;
    };
}

export interface FakeAnalysisPayload {
    highlights?: string[];
    improvement_areas?: string[];
    recommended_focus?: string[];
    next_steps?: string[];
    [key: string]: unknown;
}

export interface AnalysisResultResponse {
    id: string;
    job_id: string;
    upload_id: string | null;
    result_kind: string;
    schema_version: string;
    title: string;
    summary: string;
    payload: FakeAnalysisPayload | StructuredAIAnalysisPayload;
    created_at: string;
}

export async function createAnalysisJob(uploadId: string) {
    return request<AnalysisJobResponse>("/api/v1/analysis-jobs", {
        method: "POST",
        body: JSON.stringify({ upload_id: uploadId }),
    });
}

export async function listAnalysisJobs() {
    return request<{ jobs: AnalysisJobResponse[]; total: number }>(
        "/api/v1/analysis-jobs",
    );
}

export async function fetchAnalysisJob(jobId: string) {
    return request<AnalysisJobResponse>(`/api/v1/analysis-jobs/${jobId}`);
}

export async function fetchAnalysisResult(jobId: string) {
    return request<AnalysisResultResponse>(
        `/api/v1/analysis-jobs/${jobId}/result`,
    );
}

export async function fetchReplayArtifact(jobId: string) {
    return request<ReplayParseArtifactResponse>(
        `/api/v1/analysis-jobs/${jobId}/replay-artifact`,
    );
}

// =============================================================================
// Strategy Knowledge / RAG
// =============================================================================

export interface KnowledgeSourceCreateRequest {
    title: string;
    source_type: "text" | "markdown" | "note" | "patch_notes" | "guide";
    content: string;
    url?: string | null;
    patch_version?: string | null;
    hero_ids?: number[];
    tags?: string[];
    metadata?: Record<string, unknown>;
}

export interface KnowledgeSourceResponse {
    id: string;
    owner_user_id: string | null;
    source_type: string;
    title: string;
    url: string | null;
    status: string;
    patch_version: string | null;
    hero_ids: number[];
    tags: string[];
    chunk_count: number;
    error_message: string | null;
    created_at: string;
    updated_at: string;
}

export interface StrategySearchResult {
    chunk_id: string;
    source_id: string;
    title: string;
    snippet: string;
    score: number;
    citation_label: string;
    url: string | null;
    patch_version: string | null;
    tags: string[];
    metadata: Record<string, unknown>;
}

export interface StrategySearchRequest {
    query: string;
    top_k?: number;
    hero_ids?: number[];
    tags?: string[];
    include_global?: boolean;
}

export async function createKnowledgeSource(data: KnowledgeSourceCreateRequest) {
    return request<KnowledgeSourceResponse>("/api/v1/knowledge-sources", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function listKnowledgeSources() {
    return request<{ sources: KnowledgeSourceResponse[]; total: number }>(
        "/api/v1/knowledge-sources",
    );
}

export async function searchStrategyKnowledge(data: StrategySearchRequest) {
    return request<{ query: string; results: StrategySearchResult[]; warnings: string[] }>(
        "/api/v1/strategy-search",
        {
            method: "POST",
            body: JSON.stringify(data),
        },
    );
}
