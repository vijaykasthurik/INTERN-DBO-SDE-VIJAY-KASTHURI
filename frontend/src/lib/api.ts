/**
 * Lumen Typed REST & Streaming API Client
 */

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

export interface User {
  id: number | string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface DatasetColumn {
  id: number | string;
  name: string;
  sanitized_name?: string;
  data_type: string;
  semantic_type?: string;
  description?: string;
  null_count?: number;
  distinct_count?: number;
  min_val?: string;
  max_val?: string;
  mean_val?: number;
  sample_values?: string[];
  profile_stats?: Record<string, unknown>;
}

export interface DataQualityReport {
  overall_score: number;
  duplicate_rows: number;
  missing_values_count: number;
  constant_columns: string[];
  impossible_values_count: number;
  details?: Record<string, unknown>;
  issues?: Array<{ category: string; severity: string; description: string }>;
}

export interface Dataset {
  id: number | string;
  name: string;
  table_name?: string;
  file_size?: number;
  row_count: number;
  column_count: number;
  quality_score?: number;
  quality_summary?: { score?: number; issues?: Array<{ category: string; severity: string; description: string }>; summary?: string };
  created_at?: string;
  columns?: DatasetColumn[];
  quality_report?: DataQualityReport;
}

export interface Relationship {
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  overlap_ratio: number;
  cardinality?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  dataset_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  route?: string;
  confidence?: "High" | "Medium" | "Low";
  chart_spec?: Record<string, unknown>;
  created_at: string;
}

export interface EvidenceEntry {
  step_id: string;
  tool: string;
  code: string;
  result_preview: unknown;
  row_count: number;
  runtime_ms: number;
  status: string;
}

export interface DashboardWidget {
  id: string;
  title: string;
  type: "kpi_card" | "chart_line" | "chart_pie" | "alert_panel" | string;
  grid_pos?: { x: number; y: number; w: number; h: number };
  data: Record<string, unknown>;
}

export interface DashboardResponse {
  id: string;
  title: string;
  widget_count: number;
  widgets: DashboardWidget[];
  scope?: string;
  scope_label?: string;
  relationships_used?: string[];
  explanation?: string;
}

export interface ReportExportResponse {
  report_id: string;
  format: "pdf" | "md";
  download_url: string;
  title: string;
}

export interface ReportArtifactItem extends ReportExportResponse {
  filename: string;
  created_at: string;
}

export interface ProviderInfo {
  available: boolean;
  type?: string;
  latency_ms?: number;
}

export interface SystemProvidersResponse {
  primary_provider: string;
  fallback_chain: string[];
  providers: Record<string, ProviderInfo>;
}

class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

function getStoredToken(): string | null {
  return localStorage.getItem("lumen_access_token");
}

export function setStoredTokens(tokens: AuthTokens | null) {
  if (tokens) {
    localStorage.setItem("lumen_access_token", tokens.access_token);
    localStorage.setItem("lumen_refresh_token", tokens.refresh_token);
  } else {
    localStorage.removeItem("lumen_access_token");
    localStorage.removeItem("lumen_refresh_token");
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }
    const detail =
      typeof errorData === "object" && errorData !== null && "detail" in errorData
        ? (errorData as { detail: unknown }).detail
        : undefined;
    const message = Array.isArray(detail)
      ? detail.map((item) => {
          if (typeof item === "string") return item;
          if (typeof item === "object" && item !== null && "msg" in item) {
            const location = "loc" in item && Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
            return `${location ? `${location}: ` : ""}${String(item.msg)}`;
          }
          return "The server rejected the request.";
        }).join("; ")
      : typeof detail === "string"
        ? detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export interface ProviderCatalogEntry {
  id: string;
  display_name: string;
  protocol: string;
  base_url: string;
  auth_style: string;
  models_endpoint: string | null;
  key_format_hint: string | null;
  docs_url: string;
  supports_tools: boolean;
  supports_json_mode: boolean;
  preferred_models: { fast: string[]; strong: string[] };
}

export interface UserApiKeyResponse {
  connected: boolean;
  provider_id?: string;
  provider_name?: string;
  masked_key?: string;
  status?: "active" | "invalid" | "quota_exhausted" | "rate_limited" | "error";
  model_fast?: string;
  model_strong?: string;
  capabilities?: Record<string, boolean>;
  last_verified_at?: number;
  last_used_at?: number;
  request_count?: number;
  status_details?: string;
  allow_shared_fallback?: boolean;
}

export interface SharedPoolStatus {
  groq_active_keys: number;
  groq_cooling_keys: number;
  zai_configured: boolean;
  hf_configured: boolean;
  user_hourly_remaining: number;
  user_hourly_limit: number;
}

export interface ValidateKeyRequest {
  provider_id: string;
  api_key: string;
  base_url?: string;
}

export interface ValidateKeyResponse {
  valid: boolean;
  status: string;
  message: string;
  models: string[];
  selected_fast: string;
  selected_strong: string;
  capabilities: Record<string, boolean>;
}

export interface ConnectKeyRequest {
  provider_id: string;
  api_key: string;
  base_url?: string;
  model_fast?: string;
  model_strong?: string;
  allow_shared_fallback?: boolean;
}

export const api = {
  auth: {
    register: (data: { email: string; password: string; full_name?: string }) =>
      request<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email: data.email, password: data.password }),
      }),
    login: async (data: { email: string; password: string }) => {
      const res = await request<AuthTokens>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: data.email, password: data.password }),
      });
      setStoredTokens(res);
      return res;
    },
    me: () => request<User>("/auth/me"),
    logout: () => {
      setStoredTokens(null);
    },
    clearData: () => request<{ message: string }>("/auth/clear-data", { method: "POST" }),
  },

  datasets: {
    list: () => request<Dataset[]>("/datasets"),
    get: (id: string | number) => request<Dataset>(`/datasets/${id}`),
    rows: (id: string | number, offset = 0, limit = 50, q = "", sort = "", direction = "asc") =>
      request<{ columns: string[]; rows: Array<Record<string, unknown>>; offset: number; limit: number; total_rows: number; column_types:Record<string,string>; column_null_counts:Record<string,number|null> }>(
        `/datasets/${id}/rows?${new URLSearchParams({offset:String(offset),limit:String(limit),q,...(sort?{sort,direction}:{})})}`
      ),
    rename: (id:string|number,name:string) => request<Dataset>(`/datasets/${id}`,{method:"PATCH",body:JSON.stringify({name})}),
    replace: (id:string|number,file:File) => {const body=new FormData();body.append("file",file);return request<Dataset>(`/datasets/${id}/replace`,{method:"POST",body});},
    upload: (formData: FormData, onProgress?: (percent:number) => void) =>
      new Promise<{datasets:Dataset[]; total_files:number; errors:Array<{file:string;error:string}>}>((resolve,reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_BASE}/upload`);
        const token = getStoredToken();
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.upload.onprogress = (event) => { if(event.lengthComputable) onProgress?.(Math.round(event.loaded / event.total * 100)); };
        xhr.onerror = () => reject(new Error("Upload connection failed. Please retry."));
        xhr.onload = () => { try { const body = JSON.parse(xhr.responseText); if(xhr.status >= 200 && xhr.status < 300) resolve(body); else reject(new Error(typeof body.detail === "string" ? body.detail : "Upload failed validation.")); } catch { reject(new Error("Upload returned an unreadable response.")); } };
        xhr.send(formData);
      }),
    delete: (id: string | number) => request<void>(`/datasets/${id}`, { method: "DELETE" }),
    relationships: () =>
      request<{ relationships: Relationship[]; total_edges: number }>(
        "/datasets/relationships"
      ).then((res) => res.relationships || []),
    updateMetrics: (id: string | number, metrics: Record<string, string>) =>
      request<Dataset>(`/datasets/${id}/metrics`, {
        method: "PATCH",
        body: JSON.stringify({ metrics }),
      }),
    updateMetric: (
      datasetId: number | string,
      data: { name: string; expression: string; description?: string }
    ) =>
      request<{ id: number; name: string; expression: string; description: string | null }>(
        `/datasets/${datasetId}/metrics`,
        {
          method: "PATCH",
          body: JSON.stringify(data),
        }
      ),
    listMetrics: (datasetId: number | string) =>
      request<Array<{ id: number; name: string; expression: string; description: string | null }>>(`/datasets/${datasetId}/metrics`),
  },

  chat: {
    listSessions: () => request<ChatSession[]>("/chat/sessions"),
    createSession: (data: { title?: string; dataset_id?: string }) =>
      request<ChatSession>("/chat/sessions", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getSession: (id: string) => request<ChatSession>(`/chat/sessions/${id}`),
    getEvidence: (messageId: string) =>
      request<EvidenceEntry[]>(`/chat/messages/${messageId}/evidence`),
    executeSQL: (sql: string) =>
      request<{ columns: string[]; rows: Array<Record<string, unknown>>; row_count: number; sanitized_sql: string; runtime_ms: number }>(
        "/chat/execute", { method: "POST", body: JSON.stringify({ sql }) }
      ),
  },

  dashboards: {
    generate: (title?: string, scope: string = "combined") =>
      request<DashboardResponse>("/dashboards/generate", {
        method: "POST",
        body: JSON.stringify({ title, scope }),
      }),
    reorder: (id:string,widget_ids:string[]) => request<{widget_ids:string[]}>(`/dashboards/${id}/order`,{method:"PATCH",body:JSON.stringify({widget_ids})}),
    get: (id: string) => request<DashboardResponse>(`/dashboards/${id}`),
  },

  reports: {
    list: () => request<ReportArtifactItem[]>("/reports"),
    export: (data: { session_id?: string; title?: string; format: "pdf" | "md"; dashboard?: DashboardResponse }) =>
      request<ReportExportResponse>("/reports/export", {
        method: "POST",
        body: JSON.stringify({
          session_id: data.session_id,
          title: data.title || "Lumen Executive Analytical Report",
          format: data.format,
          dashboard: data.dashboard,
        }),
      }),
    downloadUrl: (filename: string) => `${API_BASE}/reports/download/${filename}`,
    download: async (downloadUrl: string) => {
      const token = getStoredToken();
      const response = await fetch(downloadUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        let message = `Report download failed (${response.status})`;
        try {
          const body = await response.json() as { detail?: unknown };
          if (typeof body.detail === "string") message = body.detail;
        } catch {
          // Preserve the HTTP status message for non-JSON errors.
        }
        throw new ApiError(message, response.status);
      }
      return response;
    },
  },

  admin: {
    health: () => request<{ status: string; version: string; environment: string }>("/health"),
    providers: () => request<SystemProvidersResponse>("/providers/status"),
  },

  byok: {
    catalog: () => request<ProviderCatalogEntry[]>("/llm/providers"),
    sharedStatus: () => request<SharedPoolStatus>("/llm/shared-status"),
    getConnection: () => request<UserApiKeyResponse>("/me/ai-connection"),
    validate: (data: ValidateKeyRequest) =>
      request<ValidateKeyResponse>("/me/ai-connection/validate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    connect: (data: ConnectKeyRequest) =>
      request<{ status: string; message: string; connection: UserApiKeyResponse }>("/me/ai-connection", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    test: () =>
      request<{ status: string; message: string; model_used: string; latency_ms: number }>("/me/ai-connection/test", {
        method: "POST",
      }),
    update: (data: { allow_shared_fallback?: boolean; model_fast?: string; model_strong?: string }) =>
      request<{ status: string; message: string }>("/me/ai-connection", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: () =>
      request<{ status: string; message: string }>("/me/ai-connection", {
        method: "DELETE",
      }),
  },
};
