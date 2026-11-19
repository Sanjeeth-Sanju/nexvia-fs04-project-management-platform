import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "../../services/api";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, AlertTriangle, Check, CheckCircle2, Clock3, Edit3, Folder, ListTodo, RotateCcw, Trash2 } from "lucide-react";

import Modal from "../../components/ui/Modal";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useToast } from "../../context/ToastContext";
import { getProjects, updateProject, updateProjectLifecycle, deleteProject } from "./projectService";
import BoardPage from "../board/BoardPage";

const list = (value) => Array.isArray(value) ? value : value?.results || [];

const emptyForm = { name: "", key: "", description: "" };

export default function ProjectDetailsPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { selectedWorkspace, selectedWorkspaceId } = useWorkspace();
  const toast = useToast();

  const [project, setProject] = useState(null);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showEdit, setShowEdit] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [lifecycleConfirmation, setLifecycleConfirmation] = useState(null);
  const [updatingLifecycle, setUpdatingLifecycle] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleting, setDeleting] = useState(false);

  const canManage = ["owner", "admin"].includes(
    selectedWorkspace?.current_user_role
  );
  const completed = project?.status === "completed";
  const isWorkspaceOwner = selectedWorkspace?.current_user_role === "owner";
  const done = issues.filter(
    (issue) => issue.status === "done" || issue.status === "completed"
  ).length;

  const load = useCallback(async () => {
    if (!selectedWorkspaceId) {
      setLoading(false);
      setProject(null);
      setIssues([]);
      return;
    }

    setLoading(true);
    try {
      const [projectResponse, issueResponse] = await Promise.all([
        getProjects(),
        // BoardPage loads the full board independently; this request is only
        // used for the project summary metrics below.
        apiRequest(`/issues/?project=${encodeURIComponent(projectId)}`),
      ]);

      const found = list(projectResponse).find(
        (item) =>
          String(item.id) === String(projectId) &&
          String(item.workspace) === String(selectedWorkspaceId)
      );

      setProject(found || null);
      setIssues(list(issueResponse).filter(
        (item) => String(item.project) === String(projectId)
      ));
    } catch (error) {
      toast.error(error.message || "Unable to load project.");
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedWorkspaceId, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    async function refreshProjectIssues(event) {
      if (String(event.detail?.projectId) !== String(projectId)) return;

      try {
        const response = await apiRequest(
          `/issues/?project=${encodeURIComponent(projectId)}`
        );
        setIssues(
          list(response).filter(
            (item) => String(item.project) === String(projectId)
          )
        );
      } catch {
        // Keep the current summary if a background refresh fails.
      }
    }

    window.addEventListener(
      "fs04:project-issues-updated",
      refreshProjectIssues
    );

    return () => {
      window.removeEventListener(
        "fs04:project-issues-updated",
        refreshProjectIssues
      );
    };
  }, [projectId]);

  function openEdit() {
    if (!canManage || completed || !project) return;
    setForm({
      name: project.name || "",
      key: project.key || "",
      description: project.description || "",
    });
    setShowEdit(true);
  }

  async function handleUpdate(event) {
    event.preventDefault();
    if (!canManage || completed || saving) return;

    const payload = {
      name: form.name.trim(),
      key: form.key.trim().toUpperCase(),
      description: form.description.trim(),
    };

    if (!payload.name || !payload.key) {
      toast.error("Project name and key are required.");
      return;
    }

    setSaving(true);
    try {
      const updatedProject = await updateProject(projectId, payload);
      setProject((current) => ({
        ...current,
        ...updatedProject,
        id: current?.id ?? Number(projectId),
      }));
      setShowEdit(false);
      toast.success("Project updated successfully.");
    } catch (error) {
      toast.error(error.message || "Unable to update project.");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdateProjectLifecycle() {
    if (!project || !lifecycleConfirmation || updatingLifecycle) return;

    const status = lifecycleConfirmation;
    setUpdatingLifecycle(true);

    try {
      const updatedProject = await updateProjectLifecycle(project.id, status);
      setProject(updatedProject);
      setLifecycleConfirmation(null);
      toast.success(
        status === "completed"
          ? `"${project.name}" marked as completed.`
          : `"${project.name}" reopened successfully.`
      );
    } catch (error) {
      toast.error(error.message || "Unable to update project status.");
    } finally {
      setUpdatingLifecycle(false);
    }
  }

  async function handleDeleteProject() {
    if (!project || deleting) return;

    if (deleteConfirmation !== project.name) {
      toast.error("Enter the exact project name to confirm deletion.");
      return;
    }

    setDeleting(true);
    try {
      await deleteProject(project.id);
      toast.success(`"${project.name}" was permanently deleted.`);
      navigate("/projects");
    } catch (error) {
      toast.error(error.message || "Unable to delete project.");
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <main className="container phase2-page">
        <div className="phase2-state">Loading project…</div>
      </main>
    );
  }

  if (!project) {
    return (
      <main className="container phase2-page">
        <Link className="phase2-back-link" to="/projects">
          <ArrowLeft size={16} /> All projects
        </Link>
        <div className="phase2-empty">
          <h2>Project not found</h2>
          <p>This project may not belong to the selected workspace.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="container phase2-page">
      <Link className="phase2-back-link" to="/projects">
        <ArrowLeft size={16} /> All projects
      </Link>

      <header className="project-details-header">
        <div className="project-details-title">
          <span className="project-details-mark">
            <Folder size={23} />
          </span>
          <div>
            <p className="phase2-eyebrow">{project.key} · PROJECT</p>
            <h1>{project.name}</h1>
            <p className="phase2-description">
              {project.description || "No project description has been added."}
            </p>
          </div>
        </div>

        <div className="project-details-actions">
          <span className={`project-lifecycle-tag${completed ? " completed" : ""}`}>
            {completed ? "Completed" : "Active"}
          </span>
          {canManage && (
            <>
              <button
                type="button"
                className="project-details-action-button"
                onClick={openEdit}
                disabled={completed}
                title="Edit project"
                aria-label="Edit project"
              >
                <Edit3 size={17} />
              </button>
              <button
                type="button"
                className={`project-details-action-button ${completed ? "is-reopen" : "is-complete"}`}
                onClick={() => setLifecycleConfirmation(completed ? "active" : "completed")}
                title={completed ? "Reopen project" : "Complete project"}
                aria-label={completed ? "Reopen project" : "Complete project"}
              >
                {completed ? <RotateCcw size={17} /> : <Check size={18} />}
              </button>
            </>
          )}
          {isWorkspaceOwner && (
            <button
              type="button"
              className="project-details-action-button is-delete"
              onClick={() => {
                setDeleteConfirmation("");
                setShowDeleteConfirmation(true);
              }}
              title="Delete project"
              aria-label="Delete project"
            >
              <Trash2 size={17} />
            </button>
          )}
        </div>
      </header>

      <section className="project-metric-grid">
        <article className="project-metric">
          <span><Folder size={17} /> Created</span>
          <strong>
            {project.created_at
              ? new Date(project.created_at).toLocaleDateString(undefined, {
                  day: "numeric",
                  month: "short",
                })
              : "—"}
          </strong>
          <small>
            {project.created_at
              ? new Date(project.created_at).getFullYear()
              : "Date unavailable"}
          </small>
        </article>
        <article className="project-metric">
          <span><ListTodo size={17} /> Total issues</span>
          <strong>{issues.length}</strong>
          <small>Tracked in this project</small>
        </article>
        <article className="project-metric">
          <span><Clock3 size={17} /> Remaining</span>
          <strong>{issues.length - done}</strong>
          <small>Not yet completed</small>
        </article>
        <article className="project-metric">
          <span><CheckCircle2 size={17} /> Completed</span>
          <strong>{done}</strong>
          <small>Completed workflow stages</small>
        </article>
      </section>

      <BoardPage embeddedProjectId={project.id} embeddedProjectStatus={project.status} />

      

      <Modal
        open={showEdit && canManage && !completed}
        onClose={() => {
          if (!saving) setShowEdit(false);
        }}
        titleId="edit-project-title"
        size="large"
      >
        <div className="projects-form-card projects-form-card--modal">
          <div className="projects-form-heading">
            <div>
              <h2 id="edit-project-title">Edit project</h2>
              <p>Update your project's name, key and description.</p>
            </div>
          </div>

          <form onSubmit={handleUpdate}>
            <label>
              Project name
              <input
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
                maxLength={150}
                required
                disabled={saving}
              />
            </label>

            <label>
              Project key
              <input
                value={form.key}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    key: event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 10),
                  }))
                }
                maxLength={10}
                required
                disabled={saving}
              />
            </label>

            <label>
              Description
              <textarea
                value={form.description}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                rows={4}
                disabled={saving}
              />
            </label>

            <div className="projects-form-actions">
              <button
                type="button"
                className="projects-cancel-button"
                onClick={() => setShowEdit(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="projects-create-button"
                disabled={saving}
              >
                {saving ? "Saving..." : "Save changes"}
              </button>
            </div>
          </form>
        </div>
      </Modal>
      {lifecycleConfirmation && (
        <div className="project-delete-overlay" role="presentation">
          <section
            className="project-lifecycle-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="project-details-lifecycle-title"
          >
            <div className="project-delete-icon">
              {lifecycleConfirmation === "completed"
                ? <CheckCircle2 size={23} />
                : <RotateCcw size={23} />}
            </div>
            <h2 id="project-details-lifecycle-title">
              {lifecycleConfirmation === "completed"
                ? "Complete this project?"
                : "Reopen this project?"}
            </h2>
            <p>
              {lifecycleConfirmation === "completed"
                ? `"${project.name}" will become read-only. Existing boards, issues and project history will remain available. You can reopen it later.`
                : `"${project.name}" will become active again, allowing the team to continue working on it.`}
            </p>
            <div className="project-lifecycle-actions">
              <button
                type="button"
                className="projects-cancel-button"
                onClick={() => setLifecycleConfirmation(null)}
                disabled={updatingLifecycle}
              >
                Cancel
              </button>
              <button
                type="button"
                className="project-lifecycle-confirm"
                onClick={handleUpdateProjectLifecycle}
                disabled={updatingLifecycle}
              >
                {updatingLifecycle
                  ? "Updating..."
                  : lifecycleConfirmation === "completed"
                    ? "Complete project"
                    : "Reopen project"}
              </button>
            </div>
          </section>
        </div>
      )}

      {showDeleteConfirmation && (
        <div className="project-delete-overlay">
          <section
            className="project-delete-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="project-details-delete-title"
          >
            <div className="project-delete-icon">
              <AlertTriangle size={23} />
            </div>
            <h2 id="project-details-delete-title">Delete this project?</h2>
            <p>
              You are about to permanently delete{" "}
              <strong>{project.name}</strong>. Its associated boards,
              sprints and issues will also be deleted. This action cannot be undone.
            </p>
            <label htmlFor="project-details-delete-confirmation">
              Type <strong>{project.name}</strong> to confirm
            </label>
            <input
              id="project-details-delete-confirmation"
              value={deleteConfirmation}
              onChange={(event) => setDeleteConfirmation(event.target.value)}
              placeholder="Enter project name"
              autoComplete="off"
              disabled={deleting}
            />
            <div className="project-delete-actions">
              <button
                type="button"
                className="projects-cancel-button"
                onClick={() => {
                  setShowDeleteConfirmation(false);
                  setDeleteConfirmation("");
                }}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="project-delete-confirm-button"
                onClick={handleDeleteProject}
                disabled={deleting || deleteConfirmation !== project.name}
              >
                {deleting ? "Deleting..." : "Permanently delete"}
              </button>
            </div>
          </section>
        </div>
      )}

    </main>
  );
}
