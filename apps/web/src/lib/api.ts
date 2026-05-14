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

export interface AnalysisResultResponse {
    id: string;
    job_id: string;
    upload_id: string | null;
    result_kind: string;
    schema_version: string;
    title: string;
    summary: string;
    payload: {
        highlights?: string[];
        improvement_areas?: string[];
        recommended_focus?: string[];
        next_steps?: string[];
        [key: string]: unknown;
    };
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
