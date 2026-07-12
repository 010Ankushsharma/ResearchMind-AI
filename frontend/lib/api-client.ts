import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { toast } from "sonner";

/**
 * Shared Axios instance for talking to the FastAPI backend.
 *
 * Base URL is intentionally relative ("/api") — next.config.js rewrites
 * `/api/*` to the backend origin in dev, and in production this app and
 * the API typically sit behind the same edge/proxy. This avoids browser
 * CORS entirely for same-origin requests.
 *
 * Every request is automatically authenticated with the current Clerk
 * session token, pulled from the global `window.Clerk` instance that
 * @clerk/nextjs attaches client-side.
 */

declare global {
  interface Window {
    Clerk?: {
      session?: {
        getToken: () => Promise<string | null>;
      };
    };
  }
}

export const apiClient = axios.create({
  baseURL: "/api",
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  if (typeof window !== "undefined" && window.Clerk?.session) {
    const token = await window.Clerk.session.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    if (status === 401) {
      toast.error("Your session expired — please sign in again.");
    } else if (status === 429) {
      toast.error("You're sending requests too quickly. Please slow down a bit.");
    } else if (status && status >= 500) {
      toast.error("Something went wrong on our end. Please try again shortly.");
    } else if (detail) {
      toast.error(detail);
    }

    return Promise.reject(error);
  }
);

/** Convenience typed wrappers — keeps call sites concise and consistent. */
export const api = {
  get: <T>(url: string, params?: Record<string, unknown>) =>
    apiClient.get<T>(url, { params }).then((res) => res.data),

  post: <T>(url: string, body?: unknown) =>
    apiClient.post<T>(url, body).then((res) => res.data),

  put: <T>(url: string, body?: unknown) =>
    apiClient.put<T>(url, body).then((res) => res.data),

  patch: <T>(url: string, body?: unknown) =>
    apiClient.patch<T>(url, body).then((res) => res.data),

  delete: <T>(url: string) => apiClient.delete<T>(url).then((res) => res.data),
};
