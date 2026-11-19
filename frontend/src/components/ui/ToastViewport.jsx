import { useEffect } from "react";
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  X,
} from "lucide-react";

const toastIcons = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

function ToastItem({ toast, onDismiss }) {
  const Icon = toastIcons[toast.type] || Info;

  useEffect(() => {
    const timer = window.setTimeout(
      () => onDismiss(toast.id),
      toast.duration
    );

    return () => window.clearTimeout(timer);
  }, [toast.id, toast.duration, onDismiss]);

  return (
    <div
      className={`app-toast app-toast-${toast.type}`}
      role={toast.type === "error" ? "alert" : "status"}
    >
      <Icon className="app-toast-icon" size={20} aria-hidden="true" />

      <p className="app-toast-message">{toast.message}</p>

      <button
        type="button"
        className="app-toast-close"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
      >
        <X size={17} />
      </button>
    </div>
  );
}

function ToastViewport({ toasts, onDismiss }) {
  return (
    <div className="app-toast-viewport" aria-label="Notifications">
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  );
}

export default ToastViewport;
