const RAW_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
const BASE = RAW_BASE.replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string, public code?: string) {
    super(message);
  }
}

export const tokenStore = {
  get: () => localStorage.getItem("mm_token"),
  set: (t: string) => localStorage.setItem("mm_token", t),
  clear: () => localStorage.removeItem("mm_token"),
};

async function request<T>(path: string, init: RequestInit = {}, isForm = false): Promise<T> {
  const headers: Record<string, string> = {};
  const t = tokenStore.get();
  if (t) headers.Authorization = `Bearer ${t}`;
  if (!isForm && init.body) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers: { ...headers, ...(init.headers as object) } });
  } catch {
    throw new ApiError(0, `Cannot reach the MeetingMind API at ${BASE}. Is the backend running?`, "network");
  }
  if (res.status === 401 && t) {
    tokenStore.clear();
    window.dispatchEvent(new Event("mm-logout"));
  }
  if (!res.ok) {
    let detail = res.statusText, code: string | undefined;
    try {
      const j = await res.json();
      code = j.code;
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail, code);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) => request<T>(p, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(p: string, body: unknown) => request<T>(p, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(p: string, body: unknown) => request<T>(p, { method: "PATCH", body: JSON.stringify(body) }),
  del: <T>(p: string) => request<T>(p, { method: "DELETE" }),
  upload: <T>(p: string, file: File) => {
    const f = new FormData();
    f.append("file", file);
    return request<T>(p, { method: "POST", body: f }, true);
  },
};
