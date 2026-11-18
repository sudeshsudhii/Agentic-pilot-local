export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";

export type Task = {
  task_id: string;
  input_text: string;
  status: string;
  risk_level?: string | null;
  parsed_intent?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
  approval_id?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
};

export type TaskEvent = {
  id: number;
  task_id: string;
  type: string;
  message: string;
  payload?: Record<string, unknown> | null;
  created_at: string;
};

export type Approval = {
  approval_id: string;
  task_id: string;
  risk_level: string;
  prompt: string;
  status: string;
  response?: string | null;
  created_at: string;
  decided_at?: string | null;
};

export type Settings = {
  setup_complete: boolean;
  ollama_base_url: string;
  ollama_model: string;
  llm_provider: string;
  active_model: string;
  debug_mode: boolean;
  auto_approve_low_risk: boolean;
};

/** Providers that run off-device, so no local model or daemon is involved. */
export const CLOUD_PROVIDERS = ["claude", "claude_cli"];

export function isCloudProvider(provider: string | undefined): boolean {
  return CLOUD_PROVIDERS.includes(provider ?? "");
}

/**
 * Human label for the active reasoning backend.
 *
 * Deliberately provider-neutral: the architecture routes planner, executor,
 * vision and recovery roles across interchangeable models, so the UI names the
 * capability rather than a vendor. Operators can see the concrete provider and
 * model in the backend health endpoint and logs.
 */
export function providerLabel(provider: string | undefined): string {
  if (!provider) return "Reasoning engine";
  if (provider === "ollama") return "Reasoning engine · on-device";
  return "Reasoning engine · hosted";
}

export type PluginManifest = {
  plugin_id: string;
  name: string;
  sites: string[];
  actions: string[];
  risk_levels: Record<string, string>;
  network_permission: boolean;
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
  }
  return response.json() as Promise<T>;
}

export async function createTask(inputText: string): Promise<{ task_id: string; status: string; stream_url: string }> {
  return request("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ input_text: inputText })
  });
}

export async function listTasks(): Promise<Task[]> {
  const body = await request<{ tasks: Task[] }>("/api/tasks");
  return body.tasks;
}

export async function getTask(taskId: string): Promise<Task> {
  return request(`/api/tasks/${taskId}`);
}

export async function cancelTask(taskId: string): Promise<Task> {
  return request(`/api/tasks/${taskId}`, { method: "DELETE" });
}

export async function resumeTask(taskId: string): Promise<Task> {
  return request(`/api/tasks/${taskId}/resume`, { method: "POST" });
}

export async function fallbackTask(taskId: string, provider: string = "duckduckgo"): Promise<Task> {
  return request(`/api/tasks/${taskId}/fallback`, {
    method: "POST",
    body: JSON.stringify({ provider })
  });
}

export async function listApprovals(): Promise<Approval[]> {
  const body = await request<{ approvals: Approval[] }>("/api/approvals");
  return body.approvals;
}

export async function respondApproval(approvalId: string, decision: "approved" | "rejected"): Promise<Approval> {
  return request(`/api/approvals/${approvalId}/respond`, {
    method: "POST",
    body: JSON.stringify({ decision })
  });
}

export async function getSettings(): Promise<Settings> {
  return request("/api/settings");
}

export async function updateSettings(settings: Partial<Settings>): Promise<Settings> {
  return request("/api/settings", {
    method: "PUT",
    body: JSON.stringify(settings)
  });
}

export async function listPlugins(): Promise<PluginManifest[]> {
  const body = await request<{ plugins: PluginManifest[] }>("/api/plugins");
  return body.plugins;
}

export type BrowserStatus = {
  open: boolean;
  task_id: string | null;
  url?: string | null;
  idle_seconds: number;
  timeout_minutes: number;
};

export async function closeBrowser(taskId: string): Promise<{ status: string; task_id: string }> {
  return request(`/api/tasks/${taskId}/close-browser`, { method: "POST" });
}

export async function getBrowserStatus(): Promise<BrowserStatus> {
  return request("/api/browser/status");
}

export type DesignJobStatus = "queued" | "generating" | "running" | "succeeded" | "failed";

export type DesignMetrics = {
  bbox_mm?: number[] | null;
  volume_mm3?: number | null;
};

export type DesignFile = {
  name: string;
  kind: string;
  size_bytes: number;
  url: string;
};

export type DesignStepInfo = {
  index: number;
  label: string;
  preview_url: string;
};

export type DesignJob = {
  job_id: string;
  status: DesignJobStatus;
  prompt: string;
  error?: string | null;
  created_at: string;
  duration_ms?: number | null;
  metrics?: DesignMetrics | null;
  script?: string | null;
  preview_url?: string | null;
  files?: DesignFile[] | null;
  steps?: DesignStepInfo[] | null;
  live?: boolean;
  live_status?: string | null;
  live_step?: string | null;
  live_step_index?: number | null;
  live_step_total?: number | null;
};

/** The API returns file/preview URLs as server-relative paths; make them loadable from the UI origin. */
export function resolveApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export type HealthComponents = {
  llm?: { provider?: string; status?: string; model?: string; latency_ms?: number } | null;
  ollama?: { status?: string; model?: string; vision_model?: string } | null;
  database?: { status?: string; tasks_count?: number; db_size_mb?: number } | null;
  browser?: { status?: string; active_sessions?: number } | null;
  features?: Record<string, boolean> | null;
};

export type DetailedHealth = {
  status: string;
  components: HealthComponents;
  uptime_seconds?: number;
  version?: string;
};

export async function getDetailedHealth(): Promise<DetailedHealth> {
  return request("/api/health/detailed");
}

export async function createDesignJob(
  prompt: string,
  live = false
): Promise<{ job_id: string; status: string }> {
  return request("/api/design/generate", {
    method: "POST",
    body: JSON.stringify({ prompt, live })
  });
}

export async function getDesignJob(jobId: string): Promise<DesignJob> {
  return request(`/api/design/jobs/${jobId}`);
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function listDesignJobs(): Promise<DesignJob[]> {
  const body = await request<{ jobs: DesignJob[] }>("/api/design/jobs");
  return body.jobs ?? [];
}
