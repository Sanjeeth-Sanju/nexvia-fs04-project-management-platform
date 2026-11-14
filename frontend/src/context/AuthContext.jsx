
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

// Shared promise prevents duplicate refresh requests
// during React StrictMode's development effect cycle.
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
      logout,
    }),
    [user, loading, login, register, logout]
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
    throw new Error("useAuth must be used inside an AuthProvider.");
  }

  return context;
}
