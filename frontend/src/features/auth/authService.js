
import {
  apiRequest,
  initializeCsrf,
  setAccessToken,
  clearAccessToken,
} from "../../services/api";

// Register a new user
export async function registerUser(userData) {
  await initializeCsrf();

  return apiRequest("/auth/register/", {
    method: "POST",
    auth: false,
    body: JSON.stringify(userData),
  });
}

// Login using username/email and password
export async function loginUser(credentials) {
  await initializeCsrf();

  const data = await apiRequest("/auth/login/", {
    method: "POST",
    auth: false,
    body: JSON.stringify(credentials),
  });

  setAccessToken(data.access_token);

  return data.user;
}

// Restore session using the HttpOnly refresh cookie
export async function refreshSession() {
  await initializeCsrf();

  const data = await apiRequest("/auth/refresh/", {
    method: "POST",
    auth: false,
    body: JSON.stringify({}),
  });

  setAccessToken(data.access_token);

  return data.access_token;
}

// Get currently authenticated user
export async function getCurrentUser() {
  return apiRequest("/auth/me/");
}

// Logout and revoke the refresh token
export async function logoutUser() {
  try {
    await initializeCsrf();

    await apiRequest("/auth/logout/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({}),
    });
  } finally {
    clearAccessToken();
  }
}
