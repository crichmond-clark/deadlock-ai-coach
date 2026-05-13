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
