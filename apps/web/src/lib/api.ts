const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | undefined>;
  devUserId?: string;
}

async function request<T>(
  path: string,
  { params, devUserId, ...options }: RequestOptions = {}
): Promise<T> {
  const url = new URL(path, API_BASE);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const headers = new Headers({
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  });

  // Dev auth bypass — pass user ID directly without real OAuth
  if (devUserId) {
    headers.set("X-Dev-User-Id", devUserId);
  }

  const response = await fetch(url.toString(), {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

// =============================================================================
// Health
// =============================================================================

export async function fetchHealth() {
  return request<{ status: string; service: string; version: string }>("/api/v1/health");
}

export async function fetchReadiness() {
  return request<{ status: string; database: string; redis: string }>("/api/v1/ready");
}

// =============================================================================
// Auth / User
// =============================================================================

export async function fetchMe(devUserId?: string) {
  return request<{ id: string; email: string | null; display_name: string | null; avatar_url: string | null }>(
    "/api/v1/me",
    { devUserId }
  );
}

// =============================================================================
// Uploads
// =============================================================================

export interface UploadKind {
  kind: "replay" | "screenshot" | "match_summary";
  filename?: string;
  content_type?: string;
  size_bytes?: number;
  storage_key?: string;
  summary_text?: string;
}

export interface UploadResponse {
  id: string;
  kind: string;
  status: string;
  filename: string | null;
  created_at: string;
}

export async function createUpload(data: UploadCreateRequest, devUserId?: string) {
  return request<UploadResponse>("/api/v1/uploads", {
    method: "POST",
    body: JSON.stringify(data),
    devUserId,
  });
}

export async function listUploads(devUserId?: string) {
  return request<{ uploads: UploadResponse[]; total: number }>("/api/v1/uploads", { devUserId });
}

export interface UploadCreateRequest {
  kind: string;
  filename?: string | null;
  content_type?: string | null;
  size_bytes?: number | null;
  storage_key?: string | null;
  summary_text?: string | null;
}