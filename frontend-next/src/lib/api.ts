import { API_URL, AUTH_BYPASS, USE_MOCKS } from "@/lib/config";
import type { ApiResult } from "@/types";

type FetchOptions = RequestInit & {
  token?: string | null;
};

// When Clerk is active, a bridge component registers a token getter here so
// apiFetch can attach the session JWT (verified by the FastAPI backend via JWKS).
type TokenGetter = () => Promise<string | null>;
let tokenGetter: TokenGetter | null = null;

export function setApiTokenGetter(getter: TokenGetter | null): void {
  tokenGetter = getter;
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {}
): Promise<ApiResult<T>> {
  const { token, headers, ...rest } = options;
  // Prefer an explicitly passed token, else pull a fresh one from Clerk (if active).
  let bearer = token ?? null;
  if (!bearer && !AUTH_BYPASS && tokenGetter) {
    try {
      bearer = await tokenGetter();
    } catch {
      bearer = null;
    }
  }
  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        ...(AUTH_BYPASS ? { "x-user-email": "demo@local.dev" } : {}),
        ...(bearer ? { Authorization: `Bearer ${bearer}` } : {}),
        ...headers,
      },
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return {
        success: false,
        error: body.error || body.detail || `Request failed (${res.status})`,
      };
    }

    const json = await res.json();
    if (json.ok === false || json.success === false) {
      return { success: false, error: json.error || json.detail || "Request failed" };
    }

    return { success: true, data: (json.data ?? json) as T };
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Network error",
    };
  }
}

export { USE_MOCKS };
