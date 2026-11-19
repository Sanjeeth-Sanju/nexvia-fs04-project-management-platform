import { useToast } from "../../context/ToastContext";
import { useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Download,
  Trash2,
  AlertTriangle,
} from "lucide-react";

import { useWorkspace } from "../../context/WorkspaceContext";
import { useAuth } from "../../context/AuthContext";
import WorkspaceMultiSelect from "./WorkspaceMultiSelect";
import {
  requestWorkspaceDataExport,
  getAccountDeletionImpact,
  confirmAccountDeletion,
} from "./settingsService";

export default function AccountActionsSections({ activeSection, onToggle }) {
  const { workspaces, loading: workspacesLoading } = useWorkspace();
  const { logout } = useAuth();
  const toast = useToast();


  const [exportWorkspaceIds, setExportWorkspaceIds] = useState([]);
  const [exportLoading, setExportLoading] = useState(false);

  const [impact, setImpact] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactError, setImpactError] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [deletionLoading, setDeletionLoading] = useState(false);
  const [deletionError, setDeletionError] = useState("");

  async function loadDeletionImpact() {
    setImpactLoading(true);
    setImpactError("");

    try {
      const result = await getAccountDeletionImpact();
      setImpact(result);
    } catch (err) {
      setImpactError(
        err.message || "Unable to load the account deletion summary."
      );
    } finally {
      setImpactLoading(false);
    }
  }

  // Load the impact summary whenever Delete Account is opened.
  useEffect(() => {
    if (activeSection === "delete" && !impact && !impactLoading) {
      loadDeletionImpact();
    }
  }, [activeSection]);

  async function handleExport(event) {
    event.preventDefault();

    if (!exportWorkspaceIds.length) {
      toast.error("Select at least one workspace to export.");
      return;
    }

    setExportLoading(true);

    try {
      const result = await requestWorkspaceDataExport(exportWorkspaceIds);
      const count = result.attachment_count || result.workspace_count || exportWorkspaceIds.length;
      const pdfLabel = `${count} workspace PDF${count === 1 ? "" : "s"}`;

      if (result.delivery === "sent") {
        toast.success(`${pdfLabel} sent to your registered email.`);
      } else if (result.delivery === "accepted_by_email_backend") {
        toast.success(
          `${pdfLabel} accepted by the email backend. Delivery is not independently confirmed.`
        );
      } else {
        toast.success("Export completed. Check your registered email address.");
      }

      setExportWorkspaceIds([]);
    } catch (err) {
      toast.error(err.message || "Unable to generate your data export.");
    } finally {
      setExportLoading(false);
    }
  }

  async function handleDeleteAccount(event) {
    event.preventDefault();
    setDeletionError("");

    if (!impact) {
      setDeletionError("Load the account deletion summary before continuing.");
      return;
    }

    if (confirmation !== impact.confirmation_phrase) {
      setDeletionError(
        `Type ${impact.confirmation_phrase} exactly to continue.`
      );
      return;
    }

    setDeletionLoading(true);

    try {
      await confirmAccountDeletion({
        current_password: currentPassword,
        confirmation,
      });

      // The account has already been deleted by the backend.
      // AuthContext clears the user even if its logout request fails.
      try {
        await logout();
      } catch {
        // The local session is still cleared by AuthContext.
      }
    } catch (err) {
      setDeletionError(err.message || "Unable to delete your account.");
      setDeletionLoading(false);
    }
  }

  return (
    <>
      <div className="settings-account-divider" />

      <button
        type="button"
        className={`settings-accordion-trigger ${activeSection === "export" ? "is-open" : ""}`}
        aria-expanded={activeSection === "export"}
        aria-controls="settings-export-panel"
        onClick={() => onToggle("export")}
      >
        <Download size={19} strokeWidth={1.9} />
        <span>Data Export</span>
        <span className="settings-accordion-chevron">
          {activeSection === "export"
            ? <ChevronDown size={19} />
            : <ChevronRight size={19} />}
        </span>
      </button>

      <div
        id="settings-export-panel"
        className={`settings-accordion-panel ${activeSection === "export" ? "is-open" : ""}`}
        aria-hidden={activeSection !== "export"}
        inert={activeSection !== "export"}
      >
        <div className="settings-accordion-panel-inner">
          <section className="settings-action-content">
            <div className="settings-section-heading">
              <span className="settings-section-icon" aria-hidden="true">
                <Download size={21} strokeWidth={1.9} />
              </span>
              <div>
                <h2>Export workspace data</h2>
                <p>
                  Receive a PDF containing the workspace information and
                  content you are authorised to access.
                </p>
              </div>
            </div>

            <form onSubmit={handleExport} className="settings-action-form">
              <label className="phase2-field">
                Select workspace
                <WorkspaceMultiSelect
                  workspaces={workspaces}
                  value={exportWorkspaceIds}
                  onChange={setExportWorkspaceIds}
                  disabled={workspacesLoading || exportLoading}
                />
                <small>
                  The PDF will be emailed to {` ${"your registered account email"}`}.
                </small>
              </label>
<div className="profile-save-row">
                <button
                  type="submit"
                  className="phase2-button phase2-button--primary"
                  disabled={
                    exportWorkspaceIds.length === 0 ||
                    workspacesLoading ||
                    exportLoading ||
                    workspaces.length === 0
                  }
                >
                  {exportLoading ? "Preparing exports..." : "Generate and email PDFs"}
                </button>
              </div>
            </form>
          </section>
        </div>
      </div>

      <div className="settings-account-divider" />

      <button
        type="button"
        className={`settings-accordion-trigger settings-accordion-trigger--danger ${activeSection === "delete" ? "is-open" : ""}`}
        aria-expanded={activeSection === "delete"}
        aria-controls="settings-delete-panel"
        onClick={() => onToggle("delete")}
      >
        <Trash2 size={19} strokeWidth={1.9} />
        <span>Delete Account</span>
        <span className="settings-accordion-chevron">
          {activeSection === "delete"
            ? <ChevronDown size={19} />
            : <ChevronRight size={19} />}
        </span>
      </button>

      <div
        id="settings-delete-panel"
        className={`settings-accordion-panel ${activeSection === "delete" ? "is-open" : ""}`}
        aria-hidden={activeSection !== "delete"}
        inert={activeSection !== "delete"}
      >
        <div className="settings-accordion-panel-inner">
          <section className="settings-action-content">
            <div className="settings-section-heading">
              <span className="settings-section-icon settings-section-icon--danger" aria-hidden="true">
                <AlertTriangle size={21} strokeWidth={1.9} />
              </span>
              <div>
                <h2>Permanently delete your account</h2>
                <p>
                  This action cannot be undone. Review the impact on your
                  workspaces before confirming.
                </p>
              </div>
            </div>

            {impactLoading && (
              <p className="settings-action-muted">Loading deletion summary...</p>
            )}

            {impactError && (
              <div>
                <p className="profile-feedback profile-feedback--error" role="alert">
                  {impactError}
                </p>
                <button
                  type="button"
                  className="phase2-button phase2-button--secondary"
                  onClick={loadDeletionImpact}
                >
                  Retry
                </button>
              </div>
            )}

            {impact && (
              <>
                <div className="settings-deletion-summary">
                  <div className="settings-deletion-counts">
                    <div>
                      <strong>{impact.owned_workspace_count}</strong>
                      <span>Owned workspaces deleted</span>
                    </div>
                    <div>
                      <strong>{impact.leaving_workspace_count}</strong>
                      <span>Workspaces you will leave</span>
                    </div>
                  </div>

                  {impact.owned_workspaces?.length > 0 && (
                    <div className="settings-deletion-list">
                      <h3>Workspaces that will be permanently deleted</h3>
                      <ul>
                        {impact.owned_workspaces.map((workspace) => (
                          <li key={workspace.id}>
                            <strong>{workspace.name}</strong>
                            <span>
                              {workspace.other_member_count} other member(s)
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {impact.leaving_workspaces?.length > 0 && (
                    <div className="settings-deletion-list">
                      <h3>Workspaces you will leave</h3>
                      <ul>
                        {impact.leaving_workspaces.map((workspace) => (
                          <li key={workspace.id}>
                            <strong>{workspace.name}</strong>
                            <span>
                              {workspace.role} · {workspace.other_member_count} other member(s)
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <p className="settings-deletion-note">
                    Owned workspaces and their content will be deleted.
                    In other workspaces, your membership will be removed and
                    shared content will remain.
                  </p>
                </div>

                <form onSubmit={handleDeleteAccount} className="settings-action-form">
                  <label className="phase2-field">
                    Current password
                    <input
                      type="password"
                      value={currentPassword}
                      onChange={(event) => setCurrentPassword(event.target.value)}
                      autoComplete="current-password"
                      required
                      disabled={deletionLoading}
                    />
                  </label>

                  <label className="phase2-field">
                    Type <strong>{impact.confirmation_phrase}</strong> to confirm
                    <input
                      type="text"
                      value={confirmation}
                      onChange={(event) => setConfirmation(event.target.value)}
                      autoComplete="off"
                      spellCheck="false"
                      required
                      disabled={deletionLoading}
                      placeholder={impact.confirmation_phrase}
                    />
                  </label>

                  {deletionError && (
                    <p className="profile-feedback profile-feedback--error" role="alert">
                      {deletionError}
                    </p>
                  )}

                  <div className="settings-delete-action">
                    <button
                      type="submit"
                      className="settings-delete-button"
                      disabled={
                        deletionLoading ||
                        !currentPassword ||
                        confirmation !== impact.confirmation_phrase
                      }
                    >
                      {deletionLoading ? "Deleting account..." : "Permanently delete account"}
                    </button>
                  </div>
                </form>
              </>
            )}
          </section>
        </div>
      </div>
    </>
  );
}
