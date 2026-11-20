import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, Check, CheckCheck, Trash2, X, Inbox, LoaderCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { createPortal } from "react-dom";
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
  clearAllNotifications,
} from "./notificationService";

function destinationFor(item) {
  const target = item.target_url;
  if (typeof target === "string" && target.startsWith("/") && !target.startsWith("//")) {
    return target;
  }

  const meta = item.metadata || {};
  if (meta.issue_id) return `/issues/${meta.issue_id}`;
  if (item.project?.id || meta.project_id) {
    return `/projects/${item.project?.id || meta.project_id}`;
  }
  if (item.workspace?.id || meta.workspace_id) return "/workspaces";
  return "/activity";
}

function relativeDate(value) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.getTime())) return "";
  const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)}d ago`;
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export default function NotificationCenter() {
  const navigate = useNavigate();
  const wrapperRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getNotifications();
      setItems(Array.isArray(data?.results) ? data.results : []);
      setUnread(Number(data?.unread_count) || 0);
    } catch (err) {
      setError(err?.message || "Unable to load notifications.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!open) return undefined;

    refresh();

    const outside = (event) => {
      if (!wrapperRef.current?.contains(event.target)) setOpen(false);
    };
    const escape = (event) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open, refresh]);

  async function markRead(item) {
    if (item.is_read) return true;
    try {
      await markNotificationRead(item.id);
      setItems((current) => current.map((entry) =>
        entry.id === item.id ? { ...entry, is_read: true } : entry
      ));
      setUnread((count) => Math.max(0, count - 1));
      return true;
    } catch (err) {
      setError(err?.message || "Could not mark as read.");
      return false;
    }
  }

  async function openItem(item) {
    const success = await markRead(item);
    if (!success) return;
    setOpen(false);
    navigate(destinationFor(item));
  }

  async function markAll() {
    if (!unread || busy) return;
    setBusy(true);
    try {
      await markAllNotificationsRead();
      setItems((current) => current.map((item) => ({ ...item, is_read: true })));
      setUnread(0);
    } catch (err) {
      setError(err?.message || "Could not mark all as read.");
    } finally {
      setBusy(false);
    }
  }

  async function removeItem(event, item) {
    event.stopPropagation();
    if (busy) return;
    setBusy(true);
    try {
      await deleteNotification(item.id);
      setItems((current) => current.filter((entry) => entry.id !== item.id));
      if (!item.is_read) setUnread((count) => Math.max(0, count - 1));
    } catch (err) {
      setError(err?.message || "Could not delete notification.");
    } finally {
      setBusy(false);
    }
  }

  async function clearAll() {
    if (!items.length || busy) return;
    setBusy(true);
    try {
      await clearAllNotifications();
      setItems([]);
      setUnread(0);
      setShowClearConfirm(false);
    } catch (err) {
      setError(err?.message || "Could not clear notifications.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="notification-center" ref={wrapperRef}>
      <button
        type="button"
        className={`topbar-icon-button notification-trigger ${open ? "is-active" : ""}`}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        title="Notifications"
        onClick={() => setOpen((value) => !value)}
      >
        <Bell size={19} />
        {unread > 0 && (
          <span className="notification-count">{unread > 99 ? "99+" : unread}</span>
        )}
      </button>

      {open && (
        <section className="notification-panel" role="dialog" aria-label="Notifications">
          <header className="notification-panel-header">
            <div>
              <h2>Notifications</h2>
              <p>{unread ? `${unread} unread` : "You're all caught up"}</p>
            </div>
            <div className="notification-panel-actions">
              {unread > 0 && (
                <button className="notification-text-action" onClick={markAll} disabled={busy}>
                  <CheckCheck size={15} /> Mark all read
                </button>
              )}
              <button className="notification-close" onClick={() => setOpen(false)} aria-label="Close">
                <X size={17} />
              </button>
            </div>
          </header>

          {error && (
            <div className="notification-error" role="alert">
              <span>{error}</span>
              <button onClick={refresh}>Retry</button>
            </div>
          )}

          <div className="notification-list">
            {loading && !items.length ? (
              <div className="notification-state">
                <LoaderCircle className="notification-spinner" size={22} />
                Loading notifications...
              </div>
            ) : !items.length ? (
              <div className="notification-state">
                <span className="notification-empty-icon"><Inbox size={24} /></span>
                <strong>No notifications yet</strong>
                <span>Updates and activity will appear here.</span>
              </div>
            ) : items.map((item) => (
              <article
                key={item.id}
                className={`notification-item ${item.is_read ? "" : "is-unread"}`}
                role="button"
                tabIndex={0}
                onClick={() => openItem(item)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") openItem(item);
                }}
              >
                <span className="notification-status-dot" />
                <div className="notification-item-content">
                  <div className="notification-item-heading">
                    <strong>{item.title}</strong>
                    <time>{relativeDate(item.created_at)}</time>
                  </div>
                  <p>{item.message}</p>
                  {item.actor?.name && (
                    <span className="notification-actor">{item.actor.name}</span>
                  )}
                </div>
                <div className="notification-item-actions">
                  {!item.is_read && (
                    <button
                      title="Mark as read"
                      aria-label="Mark as read"
                      disabled={busy}
                      onClick={async (event) => {
                        event.stopPropagation();
                        await markRead(item);
                      }}
                    >
                      <Check size={15} />
                    </button>
                  )}
                  <button
                    title="Delete notification"
                    aria-label="Delete notification"
                    disabled={busy}
                    onClick={(event) => removeItem(event, item)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </article>
            ))}
          </div>

          {items.length > 0 && (
            <footer className="notification-panel-footer">
              <span>{items.length} recent notifications</span>
              <button
                className="notification-text-action notification-clear-action"
                onClick={() => setShowClearConfirm(true)}
                disabled={busy}
              >
                <Trash2 size={14} /> Clear all
              </button>
            </footer>
          )}
        </section>
      )}

      {showClearConfirm && createPortal((
        <div
          className="notification-confirm-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !busy) {
              setShowClearConfirm(false);
            }
          }}
        >
          <section
            className="notification-confirm-modal"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="notification-confirm-title"
            aria-describedby="notification-confirm-description"
          >
            <div className="notification-confirm-icon">
              <Trash2 size={22} />
            </div>

            <h2 id="notification-confirm-title">
              Clear all notifications?
            </h2>

            <p id="notification-confirm-description">
              This will permanently remove all your notifications.
              This action cannot be undone.
            </p>

            <div className="notification-confirm-actions">
              <button
                type="button"
                className="notification-confirm-cancel"
                onClick={() => setShowClearConfirm(false)}
                disabled={busy}
              >
                Cancel
              </button>

              <button
                type="button"
                className="notification-confirm-delete"
                onClick={clearAll}
                disabled={busy}
              >
                {busy ? "Clearing..." : "Clear notifications"}
              </button>
            </div>
          </section>
        </div>
      ), document.body)}
    </div>
  );
}
