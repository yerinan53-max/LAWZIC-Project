const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8080/api";

export function getToken() { return sessionStorage.getItem("accessToken"); }
export function setToken(token) { sessionStorage.setItem("accessToken", token); }
export function clearToken() { sessionStorage.removeItem("accessToken"); }

export async function api(path, options = {}) {
  const headers = new Headers(options.headers ?? {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message ?? error.detail ?? "요청 처리에 실패했습니다.");
  }
  return response.status === 204 ? null : response.json();
}
