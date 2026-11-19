const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"
).replace(/\/+$/, "");

let accessToken = null;
let refreshPromise = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function clearAccessToken() {
  accessToken = null;
}

function getCsrfToken() {
  const csrfCookie = document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith("csrftoken="));

  return csrfCookie
    ? decodeURIComponent(csrfCookie.split("=").slice(1).join("="))
    : null;
}

export async function initializeCsrf() {
  const response = await fetch(`${API_BASE_URL}/auth/csrf/`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error("Unable to initialize CSRF protection.");
  }

  const csrfToken = getCsrfToken();

  if (!csrfToken) {
    throw new Error("CSRF cookie was not received.");
  }

  return csrfToken;
}

export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function parseResponse(response) {
  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";

  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message =
      typeof data === "object" && data !== null
        ? data.detail || data.message || "Something went wrong."
        : data || "Something went wrong.";

    const error = new ApiError(message, response.status, data);
    const errorCode =
      typeof data === "object" && data !== null
        ? String(data.code || data.error_code || "")
        : "";

    error.isPlanLimit =
      errorCode === "plan_limit_reached" ||
      (
        response.status === 403 &&
        /plan.?limit|quota|subscription.?limit|upgrade.?required/i.test(errorCode)
      ) ||
      (
        response.status === 403 &&
        /plan limit|subscription limit|upgrade your plan|upgrade your subscription|quota exceeded/i.test(message)
      );

    if (error.isPlanLimit) {
      window.dispatchEvent(new CustomEvent("billing:upgrade-required", {
        detail: { message, data },
      }));
    }

    throw error;
  }

  return data;
}

function notifySessionExpired() {
  clearAccessToken();
  window.dispatchEvent(new Event("auth:session-expired"));
}

async function refreshAccessToken() {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const csrfToken = await initializeCsrf();

    const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({}),
    });

    if (response.status === 401) {
      notifySessionExpired();
      return false;
    }

    const data = await parseResponse(response);

    if (!data?.access_token) {
      throw new Error("Refresh response did not contain an access token.");
    }

    setAccessToken(data.access_token);
    return true;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

async function performRequest(path, options, token) {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});

  headers.set("Accept", "application/json");

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else {
    headers.delete("Authorization");
  }

  const unsafeMethods = ["POST", "PUT", "PATCH", "DELETE"];

  if (unsafeMethods.includes(method)) {
    const csrfToken = getCsrfToken();

    if (!csrfToken) {
      throw new Error("CSRF token missing. Initialize CSRF first.");
    }

    headers.set("X-CSRFToken", csrfToken);
  }

  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });
}

export async function apiRequest(path, options = {}) {
  const { auth = true, ...fetchOptions } = options;

  const tokenUsed = auth ? accessToken : null;

  let response = await performRequest(
    path,
    fetchOptions,
    tokenUsed
  );

  // Only authenticated requests may trigger automatic refresh.
  // Never retry login, registration, refresh or logout requests.
  if (response.status === 401 && auth) {
    // Another request may already have refreshed the token.
    if (accessToken && accessToken !== tokenUsed) {
      response = await performRequest(
        path,
        fetchOptions,
        accessToken
      );
    } else {
      const refreshed = await refreshAccessToken();

      if (refreshed) {
        response = await performRequest(
          path,
          fetchOptions,
          accessToken
        );
      }
    }
  }

  return parseResponse(response);
}
