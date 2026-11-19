import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

import ToastViewport from "../components/ui/ToastViewport";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback((type, message, duration) => {
    const isPlanLimit =
      type === "error" &&
      /plan limit|subscription limit|upgrade your plan|upgrade your subscription|quota exceeded/i.test(
        String(message || "")
      );

    if (isPlanLimit) return null;

    const id = ++nextId.current;

    setToasts((current) => [
      ...current,
      {
        id,
        type,
        message,
        duration: duration ?? (type === "error" ? 5000 : 3500),
      },
    ]);

    return id;
  }, []);

  const toast = useMemo(
    () => ({
      success: (message, duration) => showToast("success", message, duration),
      error: (message, duration) => showToast("error", message, duration),
      warning: (message, duration) => showToast("warning", message, duration),
      info: (message, duration) => showToast("info", message, duration),
      dismiss: dismissToast,
    }),
    [showToast, dismissToast]
  );

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used inside a ToastProvider.");
  }

  return context;
}
