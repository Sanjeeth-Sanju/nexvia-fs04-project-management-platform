
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  loginUser,
  registerUser,
  refreshSession,
  getCurrentUser,
  logoutUser,
} from "../features/auth/authService";

const AuthContext = createContext(null);

// Prevent duplicate refresh requests during React StrictMode.
let sessionRestorePromise = null;

function restoreSession() {
  if (!sessionRestorePromise) {
    sessionRestorePromise = (async () => {
      try {
        await refreshSession();
        return await getCurrentUser();
      } catch {
        return null;
      } finally {
        sessionRestorePromise = null;
      }
    })();
  }

  return sessionRestorePromise;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Listen for an expired or invalid refresh session.
  useEffect(() => {
    function handleSessionExpired() {
      setUser(null);
      setLoading(false);
    }

    window.addEventListener(
      "auth:session-expired",
      handleSessionExpired
    );

    return () => {
      window.removeEventListener(
        "auth:session-expired",
        handleSessionExpired
      );
    };
  }, []);

  // Restore an existing session when the app starts.
  useEffect(() => {
    let isMounted = true;

    async function initializeAuth() {
      const currentUser = await restoreSession();

      if (isMounted) {
        setUser(currentUser);
        setLoading(false);
      }
    }

    initializeAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  // Login
  const login = useCallback(async (credentials) => {
    const authenticatedUser = await loginUser(credentials);

    setUser(authenticatedUser);

    return authenticatedUser;
  }, []);

  // Registration
  const register = useCallback(async (userData) => {
    return registerUser(userData);
  }, []);

  // Update the authenticated user across the application.
  const updateUser = useCallback((updatedFields) => {
    setUser((currentUser) =>
      currentUser ? { ...currentUser, ...updatedFields } : currentUser
    );
  }, []);

  // Logout
  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      register,
      updateUser,
      logout,
    }),
    [user, loading, login, register, updateUser, logout]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside an AuthProvider."
    );
  }

  return context;
}
