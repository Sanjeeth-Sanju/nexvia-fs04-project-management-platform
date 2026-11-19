import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Edit3, Trash2 } from "lucide-react";
import { useWorkspace } from "../../context/WorkspaceContext";
import Modal from "../../components/ui/Modal";
import { useToast } from "../../context/ToastContext";
import { updateWorkspace } from "./workspaceService";

function WorkspacePage() {
  const toast = useToast();
  const navigate = useNavigate();

  const {
    workspaces,
    selectedWorkspaceId,
    selectWorkspace,
    createWorkspace,
    deleteWorkspace,
    refreshWorkspaces,
    loading,
    error: workspaceError,
  } = useWorkspace();

  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [workspaceToDelete, setWorkspaceToDelete] = useState(null);
  const [confirmationName, setConfirmationName] = useState("");
  const [workspaceToEdit, setWorkspaceToEdit] = useState(null);
  const [editName, setEditName] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  function handleWorkspaceSelect(workspaceId) {
    if (String(workspaceId) === String(selectedWorkspaceId)) return;
    selectWorkspace(workspaceId);
    navigate("/dashboard", { replace: true });
  }

  useEffect(() => {
    if (workspaceError) toast.error(workspaceError);
  }, [workspaceError, toast]);


  async function handleCreate(event) {
    event.preventDefault();
    const trimmedName = name.trim();

    if (!trimmedName) {
      toast.error("Please enter a workspace name.");
      return;
    }

    setCreating(true);

    try {
      await createWorkspace(trimmedName);
      setName("");
      toast.success("Workspace created successfully.");
    } catch (err) {
      // Plan-limit errors already open the global upgrade modal via apiRequest.
      if (!err.isPlanLimit) {
        toast.error(err.message || "Unable to create workspace.");
      }
    } finally {
      setCreating(false);
    }
  }

  async function handleWorkspaceEdit(event) {
    event.preventDefault();
    if (!workspaceToEdit || !editName.trim()) return;
    setSavingEdit(true);
    try {
      await updateWorkspace(workspaceToEdit.id, { name: editName.trim() });
      await refreshWorkspaces();
      toast.success("Workspace updated successfully.");
      setWorkspaceToEdit(null);
      setEditName("");
    } catch (err) {
      toast.error(err.message || "Unable to update workspace.");
    } finally {
      setSavingEdit(false);
    }
  }

  function closeDeleteModal() {
    if (deletingId !== null) return;
    setWorkspaceToDelete(null);
    setConfirmationName("");
  }

  async function handleDelete() {
    if (!workspaceToDelete) return;
    if (confirmationName.trim() !== workspaceToDelete.name) return;

    const workspace = workspaceToDelete;

    setDeletingId(workspace.id);

    try {
      await deleteWorkspace(workspace.id);
      toast.success(`"${workspace.name}" was permanently deleted.`);
      setWorkspaceToDelete(null);
      setConfirmationName("");
    } catch (err) {
      toast.error(err.message || "Unable to delete workspace.");
    } finally {
      setDeletingId(null);
    }
  }

  if (loading) {
    return (
      <main className="container workspace-page">
        <p>Loading workspaces...</p>
      </main>
    );
  }

  return (
    <main className="container workspace-page">
      <header className="workspace-page-header">
        <div>
          <p className="workspace-eyebrow">ORGANIZATION</p>
          <h1>Workspaces</h1>
          <p className="workspace-description">
            Create and manage the spaces where your team collaborates.
          </p>
        </div>

        <span className="workspace-count">
          {workspaces.length} {workspaces.length === 1 ? "workspace" : "workspaces"}
        </span>
      </header>

      <section className="workspace-create-card">
        <div>
          <h2>Create a workspace</h2>
          <p>Start a separate space for an organization or team.</p>
        </div>

        <form className="workspace-create-form" onSubmit={handleCreate}>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Nexvia Technologies"
            maxLength={150}
            aria-label="Workspace name"
            disabled={creating}
          />

          <button type="submit" disabled={creating || !name.trim()}>
            {creating ? "Creating..." : "Create workspace"}
          </button>
        </form>
      </section>

      <section className="workspace-list-section">
        <div className="workspace-section-heading">
          <h2>Your workspaces</h2>
          <p>Select a workspace to make it your active workspace.</p>
        </div>

        {workspaces.length === 0 ? (
          <div className="workspace-empty-state">
            <h3>No workspaces yet</h3>
            <p>Create your first workspace to get started.</p>
          </div>
        ) : (
          <div className="workspace-card-list">
            {workspaces.map((workspace) => {
              const isActive =
                String(workspace.id) === String(selectedWorkspaceId);

              return (
                <article
                  className={`workspace-management-card${isActive ? " is-active" : ""}`}
                  key={workspace.id}
                >
                  <div className="workspace-card-identity">
                    <div className="workspace-card-icon">
                      {workspace.name?.charAt(0).toUpperCase() || "W"}
                    </div>

                    <div className="workspace-card-details">
                      <h3>{workspace.name}</h3>
                      <p>
                        {workspace.slug}
                        {workspace.created_at && (
                          <> · Created {new Date(workspace.created_at).toLocaleDateString()}</>
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="workspace-card-actions">
                    {isActive ? (
                      <span className="workspace-active-label">
                        Active workspace
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="workspace-select-button"
                        onClick={() => handleWorkspaceSelect(workspace.id)}
                      >
                        Switch to workspace
                      </button>
                    )}

                    {workspace.current_user_role === "owner" && (
                      <>
                      <button
                        type="button"
                        className="workspace-edit-icon-button"
                        aria-label={`Edit ${workspace.name}`}
                        title={`Edit ${workspace.name}`}
                        onClick={() => {
                          setWorkspaceToEdit(workspace);
                          setEditName(workspace.name || "");
                        }}
                      >
                        <Edit3 size={16} />
                      </button>
                      <button
                        type="button"
                        className="workspace-delete-button"
                        onClick={() => {
                          setWorkspaceToDelete(workspace);
                          setConfirmationName("");
                        }}
                      >
                        <Trash2 size={14} />
                        Delete
                      </button>
                      </>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <Modal
        open={Boolean(workspaceToEdit)}
        onClose={() => !savingEdit && setWorkspaceToEdit(null)}
        titleId="workspace-edit-title"
        size="small"
      >
        {workspaceToEdit && (
          <form className="workspace-edit-form" onSubmit={handleWorkspaceEdit}>
            <h2 id="workspace-edit-title">Edit workspace</h2>
            <p className="workspace-modal-description">Update the name of {workspaceToEdit.name}.</p>
            <label className="workspace-confirm-label" htmlFor="workspace-edit-name">Workspace name</label>
            <input
              id="workspace-edit-name"
              className="workspace-confirm-input"
              type="text"
              value={editName}
              onChange={(event) => setEditName(event.target.value)}
              maxLength={150}
              required
              autoFocus
              disabled={savingEdit}
            />
            <div className="workspace-modal-actions">
              <button type="button" className="workspace-modal-cancel" onClick={() => setWorkspaceToEdit(null)} disabled={savingEdit}>Cancel</button>
              <button type="submit" className="workspace-select-button" disabled={savingEdit || !editName.trim() || editName.trim() === workspaceToEdit.name}>
                {savingEdit ? "Saving..." : "Save changes"}
              </button>
            </div>
          </form>
        )}
      </Modal>

      <Modal
        open={Boolean(workspaceToDelete)}
        onClose={closeDeleteModal}
        titleId="workspace-delete-title"
        size="medium"
      >
        {workspaceToDelete && (
          <>
            <div className="workspace-modal-warning-icon">
              <AlertTriangle size={25} />
            </div>

            <h2 id="workspace-delete-title">Delete workspace?</h2>

            <p className="workspace-modal-description">
              You are about to permanently delete{" "}
              <strong>{workspaceToDelete.name}</strong>.
            </p>

            <div className="workspace-modal-consequences">
              <p>This will permanently remove:</p>
              <ul>
                <li>All projects and issues</li>
                <li>Team memberships and invitations</li>
                <li>Workspace activity and workflow statuses</li>
                <li>Other records associated with this workspace</li>
              </ul>
            </div>

            <label className="workspace-confirm-label">
              Type <strong>{workspaceToDelete.name}</strong> to confirm
            </label>

            <input
              className="workspace-confirm-input"
              type="text"
              value={confirmationName}
              onChange={(event) => setConfirmationName(event.target.value)}
              placeholder="Enter workspace name"
              autoFocus
              disabled={deletingId !== null}
            />

            <div className="workspace-modal-actions">
              <button
                type="button"
                className="workspace-modal-cancel"
                onClick={closeDeleteModal}
                disabled={deletingId !== null}
              >
                Cancel
              </button>

              <button
                type="button"
                className="workspace-modal-delete"
                onClick={handleDelete}
                disabled={
                  confirmationName.trim() !== workspaceToDelete.name ||
                  deletingId !== null
                }
              >
                <Trash2 size={15} />
                {deletingId !== null ? "Deleting..." : "Delete workspace"}
              </button>
            </div>
          </>
        )}
      </Modal>
    </main>
  );
}

export default WorkspacePage;
