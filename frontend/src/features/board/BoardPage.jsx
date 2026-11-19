import BoardSelect from "./components/BoardSelect";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { LayoutGrid, Plus, X } from "lucide-react";

import { useWorkspace } from "../../context/WorkspaceContext";
import { useToast } from "../../context/ToastContext";
import { getProjects } from "../projects/projectService";
import {
  getBoards,
  createBoard,
  getWorkflowStatuses,
} from "./boardService";
import { getIssues, createIssue, moveIssue } from "../issues/issueService";
import BoardToolbar from "./components/BoardToolbar";
import BoardColumn from "./components/BoardColumn";
import SprintManager from "./components/SprintManager";

function getList(response) {
  return Array.isArray(response) ? response : response?.results || [];
}

const initialIssueForm = {
  title: "",
  description: "",
  issue_type: "task",
  priority: "medium",
};

export default function BoardPage({ embeddedProjectId = null, embeddedProjectStatus = null } = {}) {
  const { selectedWorkspace, selectedWorkspaceId } = useWorkspace();
  const navigate = useNavigate();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [projects, setProjects] = useState([]);
  const [boards, setBoards] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creatingBoard, setCreatingBoard] = useState(false);
  const [showIssueForm, setShowIssueForm] = useState(false);
  const [issueStatus, setIssueStatus] = useState("");
  const [creatingIssue, setCreatingIssue] = useState(false);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(initialIssueForm);

  const selectedProjectId = embeddedProjectId != null
    ? String(embeddedProjectId)
    : searchParams.get("project") || "";
  const selectedProject = projects.find(
    (project) => String(project.id) === String(selectedProjectId)
  );
  const board = boards.find(
    (item) => String(item.project) === String(selectedProjectId)
  );
  const isReadOnly = embeddedProjectId != null
    ? embeddedProjectStatus === "completed"
    : selectedProject?.status === "completed";

  const canManageBoards = ["owner", "admin"].includes(
    selectedWorkspace?.current_user_role
  );

  const loadBoardData = useCallback(async () => {
    if (!selectedWorkspaceId) {
      setProjects([]);
      setBoards([]);
      setStatuses([]);
      setIssues([]);
      setLoading(false);
      return;
    }

    setLoading(true);

    try {
      const [projectResponse, boardResponse, statusResponse, issueResponse] =
        await Promise.all([
          getProjects(),
          getBoards(),
          getWorkflowStatuses(selectedWorkspaceId),
          getIssues(),
        ]);

      const workspaceProjects = getList(projectResponse).filter(
        (project) =>
          String(project.workspace) === String(selectedWorkspaceId)
      );

      const projectIds = new Set(
        workspaceProjects.map((project) => String(project.id))
      );

      setProjects(workspaceProjects);
      setBoards(
        getList(boardResponse).filter((item) =>
          projectIds.has(String(item.project))
        )
      );
      setStatuses(getList(statusResponse).sort(
        (a, b) => a.position - b.position
      ));
      setIssues(
        getList(issueResponse).filter((issue) =>
          projectIds.has(String(issue.project))
        )
      );
    } catch (error) {
      toast.error(error.message || "Unable to load the board.");
    } finally {
      setLoading(false);
    }
  }, [selectedWorkspaceId, toast]);

  useEffect(() => {
    loadBoardData();
  }, [loadBoardData]);

  useEffect(() => {
    if (embeddedProjectId) return;
    if (
      projects.length &&
      !projects.some((project) => String(project.id) === selectedProjectId)
    ) {
      setSearchParams({ project: String(projects[0].id) }, { replace: true });
    }
  }, [projects, selectedProjectId, setSearchParams, embeddedProjectId]);

  async function handleCreateBoard() {
    if (!selectedProject || isReadOnly) return;

    setCreatingBoard(true);
    try {
      await createBoard({
        project: selectedProject.id,
        name: `${selectedProject.name} Board`,
      });
      toast.success("Board created successfully.");
      await loadBoardData();
    } catch (error) {
      toast.error(error.message || "Unable to create board.");
    } finally {
      setCreatingBoard(false);
    }
  }

  function openIssueForm(status = statuses.find((item) => item.slug)?.slug || "") {
    if (isReadOnly) return;
    setIssueStatus(status);
    setForm(initialIssueForm);
    setShowIssueForm(true);
  }

  async function handleCreateIssue(event) {
    event.preventDefault();

    if (isReadOnly) return;

    const resolvedBoard = boards.find(
      (item) => String(item.project?.id ?? item.project) === String(selectedProject?.id)
    );
    const resolvedStatus = statuses.find(
      (item) => item.slug === issueStatus
    )?.slug || statuses[0]?.slug;

    if (!resolvedBoard || !selectedProject || !resolvedStatus) {
      toast.error("This project needs a board and at least one workflow status before issues can be created.");
      return;
    }

    setCreatingIssue(true);
    try {
      const issue = await createIssue({
        ...form,
        project: Number(selectedProject.id),
        board: Number(resolvedBoard.id),
        status: resolvedStatus,
      });

      setIssues((current) => [...current, issue]);
      window.dispatchEvent(
        new CustomEvent("fs04:project-issues-updated", {
          detail: { projectId: selectedProject.id },
        })
      );
      setShowIssueForm(false);
      setForm(initialIssueForm);
      toast.success("Issue created.");
    } catch (error) {
      toast.error(error.message || "Unable to create issue.");
    } finally {
      setCreatingIssue(false);
    }
  }

  function handleDragStart(event, issue) {
    event.dataTransfer.setData("text/plain", String(issue.id));
    event.dataTransfer.effectAllowed = "move";
  }

  async function handleDrop(event, targetStatus, targetIssue = null) {
    event.preventDefault();
    event.stopPropagation();

    if (isReadOnly) return;

    const issueId = event.dataTransfer.getData("text/plain");
    const issue = issues.find((item) => String(item.id) === issueId);

    if (!issue || (targetIssue && String(targetIssue.id) === issueId)) {
      return;
    }

    const sameProject = (item) =>
      String(item.project) === String(issue.project);

    const byPosition = (a, b) =>
      (Number(a.position) || 0) - (Number(b.position) || 0) ||
      Number(a.id) - Number(b.id);

    const previousIssues = issues;

    const targetLane = issues
      .filter(
        (item) =>
          sameProject(item) &&
          item.status === targetStatus.slug &&
          String(item.id) !== issueId
      )
      .sort(byPosition);

    let insertAt = targetLane.length;

    if (targetIssue) {
      const targetIndex = targetLane.findIndex(
        (item) => String(item.id) === String(targetIssue.id)
      );

      if (targetIndex < 0) return;

      const rect = event.currentTarget.getBoundingClientRect();
      const dropAfter = event.clientY > rect.top + rect.height / 2;

      insertAt = targetIndex + (dropAfter ? 1 : 0);
    }

    insertAt = Math.max(0, Math.min(insertAt, targetLane.length));

    const reordered = new Map();

    if (issue.status !== targetStatus.slug) {
      const sourceLane = issues
        .filter(
          (item) =>
            sameProject(item) &&
            item.status === issue.status &&
            String(item.id) !== issueId
        )
        .sort(byPosition);

      sourceLane.forEach((item, index) => {
        reordered.set(item.id, {
          status: item.status,
          position: index,
        });
      });
    }

    targetLane.splice(insertAt, 0, issue);

    targetLane.forEach((item, index) => {
      reordered.set(item.id, {
        status: targetStatus.slug,
        position: index,
      });
    });

    setIssues((current) =>
      current.map((item) =>
        reordered.has(item.id)
          ? { ...item, ...reordered.get(item.id) }
          : item
      )
    );

    try {
      await moveIssue(issue.id, {
        status: targetStatus.slug,
        position: insertAt,
      });

      window.dispatchEvent(
        new CustomEvent("fs04:project-issues-updated", {
          detail: { projectId: issue.project },
        })
      );

      if (issue.status === targetStatus.slug) {
        toast.success("Issue order updated.");
      } else {
        toast.success(`Moved to ${targetStatus.name}.`);
      }
    } catch (error) {
      setIssues(previousIssues);
      toast.error(error.message || "Unable to update issue order.");
    }
  }

  const visibleIssues = useMemo(() => {
    const query = search.trim().toLowerCase();

    return issues
      .filter((issue) => {
        if (String(issue.project) !== String(selectedProjectId)) return false;
        if (!query) return true;

        return `${issue.title} ${issue.description || ""} ${issue.priority}`
          .toLowerCase()
          .includes(query);
      })
      .sort(
        (a, b) =>
          (Number(a.position) || 0) - (Number(b.position) || 0) ||
          Number(a.id) - Number(b.id)
      );
  }, [issues, search, selectedProjectId]);

  if (loading) {
    return embeddedProjectId
      ? <div className="kanban-page"><p>Loading board...</p></div>
      : <main className="container kanban-page"><p>Loading board...</p></main>;
  }

  const PageWrapper = embeddedProjectId ? "div" : "main";

  return (
    <PageWrapper className={embeddedProjectId ? "kanban-page kanban-page--embedded" : "container kanban-page"}>
      {!embeddedProjectId && <header className="kanban-page-header">
        <div>
          <p className="projects-eyebrow">PROJECT MANAGEMENT</p>
          <Link to="/projects" className="board-back-link">← Back to projects</Link>
              <h1>Board</h1>
          <p>Plan, organize and track your team's work.</p>
        </div>
      </header>}

      {!selectedWorkspaceId ? (
        <div className="kanban-empty-state">
          <LayoutGrid size={34} />
          <h2>No workspace selected</h2>
          <p>Select a workspace to view its project boards.</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="kanban-empty-state">
          <LayoutGrid size={34} />
          <h2>No projects yet</h2>
          <p>Create a project before setting up a board.</p>
        </div>
      ) : (
        <>
          {selectedProject && (
        <SprintManager
          projectId={selectedProject.id}
          canManage={canManageBoards}
          readOnly={isReadOnly}
        />
      )}

      <BoardToolbar
            projects={projects}
            selectedProjectId={selectedProjectId}
            onProjectChange={(id) => setSearchParams({ project: id })}
            search={search}
            onSearchChange={setSearch}
            onCreateIssue={isReadOnly ? null : () => openIssueForm()}
            showProjectSelect={!embeddedProjectId}
          />

          {!embeddedProjectId && selectedProject && (
            <div className="kanban-project-heading">
              <div>
                <h2>{selectedProject.name}</h2>
                {selectedProject.description?.trim() &&
                  selectedProject.description.trim().toLowerCase() !== selectedProject.name.trim().toLowerCase() &&
                  selectedProject.description.trim().toLowerCase() !== selectedProject.key?.trim().toLowerCase() && (
                    <p>{selectedProject.description}</p>
                  )}
              </div>
            </div>
          )}

          {!board ? (
            <div className="kanban-empty-state">
              <LayoutGrid size={34} />
              <h2>No board for this project</h2>
              <p>
                {isReadOnly
                  ? "This project is completed. Its existing work remains available in read-only mode."
                  : `Create a board to start managing issues in ${selectedProject?.name}.`}
              </p>
              {canManageBoards && !isReadOnly && (
                <button
                  type="button"
                  className="kanban-primary-button"
                  onClick={handleCreateBoard}
                  disabled={creatingBoard}
                >
                  <Plus size={16} />
                  {creatingBoard ? "Creating..." : "Create board"}
                </button>
              )}
              {!canManageBoards && (
                <p>Ask a workspace owner or admin to create the project board.</p>
              )}
            </div>
          ) : statuses.length === 0 ? (
            <div className="kanban-empty-state">
              <h2>No workflow statuses configured</h2>
              <p>Ask a workspace owner or admin to configure workflow statuses.</p>
            </div>
          ) : (
            <div className="kanban-board">
              {statuses.map((status) => (
                <BoardColumn
                  key={status.id}
                  status={status}
                  issues={visibleIssues.filter(
                    (issue) => issue.status === status.slug
                  )}
                  onDrop={handleDrop}
                  onDragStart={handleDragStart}
                  onIssueClick={(issue) =>
                    navigate(`/issues/${issue.id}`)
                  }
                  onAddIssue={openIssueForm}
                  readOnly={isReadOnly}
                />
              ))}
            </div>
          )}
        </>
      )}

      {showIssueForm && !isReadOnly && (
        <div className="kanban-modal-overlay">
          <section
            className="kanban-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="kanban-issue-title"
          >
            <header>
              <div>
                <p className="projects-eyebrow">NEW WORK ITEM</p>
                <h2 id="kanban-issue-title">Create issue</h2>
              </div>
              <button
                type="button"
                className="kanban-icon-button"
                onClick={() => setShowIssueForm(false)}
                aria-label="Close"
              >
                <X size={19} />
              </button>
            </header>

            <form onSubmit={handleCreateIssue}>
              <label>
                Issue title
                <input
                  value={form.title}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, title: event.target.value }))
                  }
                  placeholder="e.g. Build authentication flow"
                  maxLength={200}
                  required
                  autoFocus
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
                  placeholder="Add details about this task..."
                  rows={4}
                />
              </label>

              <div className="kanban-form-row">
                <label>
                  Type
                  <BoardSelect
                    label="Select type"
                    value={form.issue_type}
                    onChange={(value) =>
                      setForm((current) => ({ ...current, issue_type: value }))
                    }
                    options={[
                      { value: "task", label: "Task" },
                      { value: "bug", label: "Bug" },
                    ]}
                  />
                </label>

                <label>
                  Priority
                  <BoardSelect
                    label="Select priority"
                    value={form.priority}
                    onChange={(value) =>
                      setForm((current) => ({ ...current, priority: value }))
                    }
                    options={[
                      { value: "low", label: "Low" },
                      { value: "medium", label: "Medium" },
                      { value: "high", label: "High" },
                      { value: "critical", label: "Critical" },
                    ]}
                  />
                </label>
              </div>

              <label>
                Initial status
                <BoardSelect
                  label="Select status"
                  value={issueStatus}
                  onChange={setIssueStatus}
                  options={statuses.map((status) => ({
                    value: status.slug,
                    label: status.name,
                  }))}
                  required
                />
              </label>

              <footer>
                <button
                  type="button"
                  className="kanban-secondary-button"
                  onClick={() => setShowIssueForm(false)}
                  disabled={creatingIssue}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="kanban-primary-button"
                  disabled={creatingIssue}
                >
                  {creatingIssue ? "Creating..." : "Create issue"}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}
    </PageWrapper>
  );
}
