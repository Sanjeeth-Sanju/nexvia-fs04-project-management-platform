import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Folder, FolderKanban, Plus, X, Trash2, AlertTriangle, Check, CheckCircle2, RotateCcw } from "lucide-react";
import Modal from "../../components/ui/Modal";

import { useWorkspace } from "../../context/WorkspaceContext";
import { useToast } from "../../context/ToastContext";
import { getProjects, createProject, deleteProject, updateProjectLifecycle } from "./projectService";
import { apiRequest } from "../../services/api";

function ProjectsPage() {
  const navigate = useNavigate();
  const { selectedWorkspace, selectedWorkspaceId } = useWorkspace();
  const toast = useToast();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [projectToUpdateLifecycle, setProjectToUpdateLifecycle] = useState(null);
  const [updatingLifecycle, setUpdatingLifecycle] = useState(false);

  const isWorkspaceOwner = selectedWorkspace?.current_user_role === "owner";
  const canManageProjects = ["owner", "admin"].includes(
    selectedWorkspace?.current_user_role
  );

  const [form, setForm] = useState({
    name: "",
    key: "",
    description: "",
  });

  useEffect(() => {
    let active = true;

    async function loadProjects() {
      if (!selectedWorkspaceId) {
        setProjects([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const response = await getProjects();
        const data = Array.isArray(response)
          ? response
          : response.results || [];

        if (active) {
          setProjects(
            data.filter(
              (project) =>
                String(project.workspace) === String(selectedWorkspaceId)
            )
          );
        }
      } catch (err) {
        if (active) {
          setError(err.message || "Unable to load projects.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadProjects();

    return () => {
      active = false;
    };
  }, [selectedWorkspaceId]);

  async function handleOpenCreateForm() {
    if (!selectedWorkspaceId) return;

    if (isWorkspaceOwner) {
      try {
        const overview = await apiRequest("/billing/overview/");
        const limit = overview?.limits?.projects_per_workspace;

        if (
          limit !== null &&
          limit !== undefined &&
          projects.length >= Number(limit)
        ) {
          window.dispatchEvent(
            new CustomEvent("billing:upgrade-required", {
              detail: {
                message: "You have reached your project limit. Upgrade your subscription to create more projects.",
                data: {
                  code: "plan_limit_reached",
                  limit: String(limit),
                  current: String(projects.length),
                },
              },
            })
          );
          return;
        }
      } catch {
        // Backend enforcement remains the fallback.
      }
    }

    setShowForm(true);
  }

  async function handleCreate(event) {
    event.preventDefault();

    const name = form.name.trim();
    const key = form.key.trim().toUpperCase();

    if (!name || !key) {
      toast.error("Project name and key are required.");
      return;
    }

    if (!/^[A-Z0-9]{1,10}$/.test(key)) {
      toast.error("Project key must contain 1–10 letters or numbers.");
      return;
    }

    setCreating(true);

    try {
      const project = await createProject({
        workspace: selectedWorkspaceId,
        name,
        key,
        description: form.description.trim(),
      });

      setProjects((current) => [...current, project]);
      setForm({ name: "", key: "", description: "" });
      setShowForm(false);
      toast.success("Project created successfully.");
    } catch (err) {
      toast.error(err.message || "Unable to create project.");
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdateProjectLifecycle() {
    if (!projectToUpdateLifecycle || updatingLifecycle) return;

    const { project, status } = projectToUpdateLifecycle;
    setUpdatingLifecycle(true);

    try {
      const updatedProject = await updateProjectLifecycle(project.id, status);
      setProjects((current) =>
        current.map((item) => item.id === project.id ? updatedProject : item)
      );
      toast.success(
        status === "completed"
          ? `"${project.name}" marked as completed.`
          : `"${project.name}" reopened successfully.`
      );
      setProjectToUpdateLifecycle(null);
    } catch (err) {
      toast.error(err.message || "Unable to update project status.");
    } finally {
      setUpdatingLifecycle(false);
    }
  }

  async function handleDeleteProject() {
    if (!projectToDelete || deleteConfirmation !== projectToDelete.name) {
      toast.error("Enter the exact project name to confirm deletion.");
      return;
    }

    setDeleting(true);
    try {
      await deleteProject(projectToDelete.id);
      setProjects((current) =>
        current.filter((project) => project.id !== projectToDelete.id)
      );
      toast.success(`"${projectToDelete.name}" was permanently deleted.`);
      setProjectToDelete(null);
      setDeleteConfirmation("");
    } catch (err) {
      toast.error(err.message || "Unable to delete project.");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <main className="container projects-page">
        <p>Loading projects...</p>
      </main>
    );
  }

  return (
    <main className="container projects-page">
      <header className="projects-page-header">
        <div>
          <p className="projects-eyebrow">WORK MANAGEMENT</p>
          <h1>Projects</h1>
          <p className="projects-description">
            Organize your team's work into projects and track progress.
          </p>

        </div>

        {canManageProjects && (
          <button
            type="button"
            className="projects-create-button"
            onClick={handleOpenCreateForm}
            disabled={!selectedWorkspaceId}
          >
            <Plus size={17} />
            Create project
          </button>
        )}
      </header>

      {error && (
        <div className="projects-error" role="alert">
          {error}
          <button type="button" onClick={() => setError("")} aria-label="Dismiss error">
            <X size={16} />
          </button>
        </div>
      )}

      <Modal
        open={showForm && canManageProjects}
        onClose={() => {
          if (!creating) {
            setShowForm(false);
            setForm({ name: "", key: "", description: "" });
          }
        }}
        titleId="create-project-title"
        size="large"
      >
        <div className="projects-form-card projects-form-card--modal">
          <div className="projects-form-heading">
            <div>
              <h2 id="create-project-title">Create a project</h2>
              <p>Set up a new project in this workspace.</p>
            </div>
          </div>

          <form onSubmit={handleCreate}>
            <label>
              Project name
              <input
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
                placeholder="e.g. Website Redesign"
                maxLength={150}
                required
                autoFocus
                disabled={creating}
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
                placeholder="Enter a unique key (e.g. WEB)"
                maxLength={10}
                minLength={1}
                required
                autoComplete="off"
                disabled={creating}
              />
              <small>Required. Use 1–10 letters or numbers. This key identifies project issues.</small>
            </label>

            <label>
              Description <span>(Optional)</span>
              <textarea
                value={form.description}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                placeholder="What is this project about?"
                rows={3}
                disabled={creating}
              />
            </label>

            <div className="projects-form-actions">
              <button
                type="button"
                className="projects-cancel-button"
                onClick={() => {
                  setShowForm(false);
                  setForm({ name: "", key: "", description: "" });
                }}
                disabled={creating}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="projects-create-button"
                disabled={creating}
              >
                {creating ? "Creating..." : "Create project"}
              </button>
            </div>
          </form>
        </div>
      </Modal>

      <section className="projects-list-section">
        <div className="projects-section-heading">
          <h2>{canManageProjects ? "All projects" : "Projects you're assigned to"}</h2>
          <span>
            {projects.length} {projects.length === 1 ? "project" : "projects"}
          </span>
        </div>

        {!selectedWorkspaceId ? (
          <div className="projects-empty-state">
            <FolderKanban size={34} />
            <h3>No workspace selected</h3>
            <p>Select or create a workspace before managing projects.</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="projects-empty-state">
            <FolderKanban size={34} />
            <h3>{canManageProjects ? "No projects yet" : "No projects assigned to you yet"}</h3>
            <p>
              {canManageProjects
                ? "Create your first project to start organizing your team's work."
                : "Ask your workspace owner or admin to assign you to a project."}
            </p>
            {canManageProjects && (
              <button
                type="button"
                className="projects-create-button"
                onClick={() => setShowForm(true)}
              >
                <Plus size={17} />
                Create your first project
              </button>
            )}
          </div>
        ) : (
          <div className="projects-grid">
            {projects.map((project) => (
              <article
                className="project-card project-card--interactive"
                key={project.id}
                role="link"
                tabIndex={0}
                onClick={() => navigate(`/projects/${project.id}`)}
                onKeyDown={(event) => {
                  if (event.target !== event.currentTarget) return;
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    navigate(`/projects/${project.id}`);
                  }
                }}
                aria-label={`Open project ${project.name}`}
              >
                <div className="project-card-top">
                  <div className="project-card-identity">
                    <div className="project-card-icon">
                      <Folder size={20} />
                    </div>
                    <span className="project-key">{project.key}</span>
                  </div>
                  {project.status === "completed" && (
                    <span
                      className="project-status project-status-completed project-status-icon"
                      data-tooltip="Completed"
                      aria-label="Completed"
                      role="img"
                      tabIndex={0}
                    >
                      <Check size={18} strokeWidth={2.5} />
                    </span>
                  )}
                </div>

                <h3>{project.name}</h3>



                <p className="project-completion-meta">
                  {project.status === "completed" && project.completed_at
                    ? `Completed ${new Date(project.completed_at).toLocaleDateString()}`
                    : "\u00a0"}
                </p>

                <div className="project-card-footer">
                  <span>
                    Created{" "}
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                  <div
                    className="project-card-footer-actions"
                    onClick={(event) => event.stopPropagation()}
                    onKeyDown={(event) => event.stopPropagation()}
                  >
                    {canManageProjects && (
                      <button
                        type="button"
                        className={`project-lifecycle-button project-lifecycle-icon-button ${project.status === "completed" ? "project-lifecycle-reopen" : "project-lifecycle-complete"}`}
                        onClick={() => setProjectToUpdateLifecycle({
                          project,
                          status: project.status === "completed" ? "active" : "completed",
                        })}
                        disabled={updatingLifecycle}
                        title={project.status === "completed" ? "Reopen this project" : "Mark project as completed"}
                        aria-label={project.status === "completed" ? "Reopen this project" : "Mark project as completed"}
                      >
                        {project.status === "completed" ? (
                          <RotateCcw size={17} />
                        ) : (
                          <Check size={17} />
                        )}
                      </button>
                    )}
                    {isWorkspaceOwner && (
                    <button
                      type="button"
                      className="project-delete-button"
                      onClick={() => {
                        setProjectToDelete(project);
                        setDeleteConfirmation("");
                      }}
                      aria-label={`Delete ${project.name}`}
                      title="Delete project"
                    >
                      <Trash2 size={16} />
                    </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    
      {projectToUpdateLifecycle && (
        <div className="project-delete-overlay" role="presentation">
          <section
            className="project-lifecycle-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="project-lifecycle-title"
          >
            <div className="project-delete-icon">
              {projectToUpdateLifecycle.status === "completed"
                ? <CheckCircle2 size={23} />
                : <RotateCcw size={23} />}
            </div>
            <h2 id="project-lifecycle-title">
              {projectToUpdateLifecycle.status === "completed"
                ? "Complete this project?"
                : "Reopen this project?"}
            </h2>
            <p>
              {projectToUpdateLifecycle.status === "completed"
                ? `"${projectToUpdateLifecycle.project.name}" will become read-only. Existing boards, issues and project history will remain available. You can reopen it later.`
                : `"${projectToUpdateLifecycle.project.name}" will become active again, allowing the team to continue working on it.`}
            </p>
            <div className="project-lifecycle-actions">
              <button
                type="button"
                className="projects-cancel-button"
                onClick={() => setProjectToUpdateLifecycle(null)}
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
                  : projectToUpdateLifecycle.status === "completed"
                    ? "Complete project"
                    : "Reopen project"}
              </button>
            </div>
          </section>
        </div>
      )}

      {projectToDelete && (
        <div className="project-delete-overlay">
          <section
            className="project-delete-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="project-delete-title"
          >
            <div className="project-delete-icon">
              <AlertTriangle size={23} />
            </div>

            <h2 id="project-delete-title">Delete this project?</h2>
            <p>
              You are about to permanently delete{" "}
              <strong>{projectToDelete.name}</strong>. Its associated boards,
              sprints and issues will also be deleted. This action cannot be undone.
            </p>

            <label htmlFor="project-delete-confirmation">
              Type <strong>{projectToDelete.name}</strong> to confirm
            </label>
            <input
              id="project-delete-confirmation"
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
                  setProjectToDelete(null);
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
                disabled={deleting || deleteConfirmation !== projectToDelete.name}
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

export default ProjectsPage;
