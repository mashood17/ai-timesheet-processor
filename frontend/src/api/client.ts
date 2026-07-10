/**
 * Thin fetch wrapper: attaches the Bearer token, handles JSON, and
 * normalizes errors into a single shape the UI can display without
 * technical jargon (Section 9 usability requirement).
 *
 * UPDATE: on any 401 from an authenticated route (never the login route
 * itself, so a wrong-password attempt still shows a normal error), this
 * now clears the stale token and redirects to /login automatically,
 * instead of leaving the user stuck re-seeing a raw "invalid token" error.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

function getToken(): string | null {
  return sessionStorage.getItem("access_token");
}

export function setToken(token: string): void {
  sessionStorage.setItem("access_token", token);
}

export function clearToken(): void {
  sessionStorage.removeItem("access_token");
}

function handleSessionExpiry(path: string): void {
  if (path.startsWith("/api/auth/login")) return; // wrong password, not an expiry
  clearToken();
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      handleSessionExpiry(path);
    }

    let detail = "Something went wrong. Please try again.";
    try {
      const errorBody = await response.json();
      detail = errorBody.detail ?? detail;
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new ApiError(detail, response.status);
  }

  return response.json() as Promise<T>;
}

export async function requestBlob(
  path: string,
  options: RequestInit = {}
): Promise<Blob> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) {
      handleSessionExpiry(path);
    }
    throw new ApiError("Could not download the file.", response.status);
  }
  return response.blob();
}

export { request };