import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { MessageSquare, Paperclip, RefreshCw, Pencil, Trash2, CheckCircle2, RotateCcw, ChevronDown, Check } from "lucide-react";

import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useToast } from "../../context/ToastContext";
import Loader from "../../components/ui/Loader";
import Modal from "../../components/ui/Modal";
import {
  getIssue,
  getIssueComments,
  createIssueComment,
  getIssueAttachments,
  uploadIssueAttachment,
  deleteIssueAttachment,
  updateIssue,
  deleteIssue,
  moveIssue,
} from "./issueService";
import { getProjects } from "../projects/projectService";
import { getWorkflowStatuses } from "../board/boardService";
import IssueDetailsPanel from "./components/IssueDetailsPanel";
import CommentForm from "../comments/components/CommentForm";
import CommentList from "../comments/components/CommentList";
import AttachmentUploader from "../attachments/components/AttachmentUploader";
import AttachmentList from "../attachments/components/AttachmentList";

function getList(response) {
  return Array.isArray(response) ? response : response?.results || [];
}

export default function IssueDetailsPage() {
  const { issueId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const { workspaces, selectedWorkspaceId, loading: workspaceLoading } = useWorkspace();

  const [issue, setIssue] = useState(null);
  const [project, setProject] = useState(null);
  const [comments, setComments] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [workflowStatuses, setWorkflowStatuses] = useState([]);
  const [editOpen, setEditOpen] = useState(false);
  const [issueTypeOpen, setIssueTypeOpen] = useState(false);
  const [priorityOpen, setPriorityOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    title: "",
    description: "",
    issue_type: "task",
    priority: "medium",
  });
  const [saving, setSaving] = useState(false);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const projectWorkspace = useMemo(() => {
    const workspaceId = project?.workspace?.id ?? project?.workspace;
    return workspaces.find(
      (workspace) => String(workspace.id) === String(workspaceId)
    ) || null;
  }, [project, workspaces]);

  const issueWorkflowStatus = workflowStatuses.find(
    (item) => item.slug === issue?.status
  );
  const issueCompleted = Boolean(issueWorkflowStatus?.is_completed);
  const isReadOnly = project?.status === "completed" || issueCompleted;
  const issueWorkspaceId = project?.workspace?.id ?? project?.workspace;
  const issueMatchesSelectedWorkspace =
    Boolean(issue && project && selectedWorkspaceId) &&
    String(issueWorkspaceId) === String(selectedWorkspaceId);
  const isWorkspaceAdmin = ["owner", "admin"].includes(
    projectWorkspace?.current_user_role
  );

  const requestSequence = useRef(0);

  const loadIssue = useCallback(async (showRefresh = false) => {
    if (workspaceLoading) return;

    const requestId = ++requestSequence.current;

    if (showRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
      setIssue(null);
      setProject(null);
      setComments([]);
      setAttachments([]);
      setWorkflowStatuses([]);
    }

    setError("");

    if (!selectedWorkspaceId) {
      setError("Select a workspace to view this issue.");
      setLoading(false);
      setRefreshing(false);
      return;
    }

    try {
      const [issueData, projectResponse] = await Promise.all([
        getIssue(issueId),
        getProjects(),
      ]);

      if (requestId !== requestSequence.current) return;

      const projectId = issueData.project?.id ?? issueData.project;
      const matchingProject = getList(projectResponse).find(
        (item) => String(item.id) === String(projectId)
      );

      const issueWorkspaceId =
        matchingProject?.workspace?.id ?? matchingProject?.workspace;

      if (
        !matchingProject ||
        String(issueWorkspaceId) !== String(selectedWorkspaceId)
      ) {
        setIssue(null);
        setProject(null);
        setComments([]);
        setAttachments([]);
        setWorkflowStatuses([]);
        setError(
          "This issue does not belong to the currently selected workspace, or you no longer have access to it."
        );
        return;
      }

      const [commentResponse, attachmentResponse, statusResponse] =
        await Promise.all([
          getIssueComments(issueId),
          getIssueAttachments(issueId),
          getWorkflowStatuses(issueWorkspaceId),
        ]);

      if (requestId !== requestSequence.current) return;

      setIssue(issueData);
      setProject(matchingProject);
      setComments(getList(commentResponse));
      setAttachments(getList(attachmentResponse));
      setWorkflowStatuses(getList(statusResponse));
    } catch (err) {
      if (requestId !== requestSequence.current) return;
      setError(err.message || "Unable to load this issue.");
      setIssue(null);
      setProject(null);
    } finally {
      if (requestId === requestSequence.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [issueId, selectedWorkspaceId, workspaceLoading]);

  useEffect(() => {
    loadIssue();
  }, [loadIssue]);

  async function handleComment(body) {
    try {
      const created = await createIssueComment(issueId, body);
      setComments((current) => [...current, created]);
      toast.success("Comment posted.");
    } catch (err) {
      toast.error(err.message || "Unable to post comment.");
      throw err;
    }
  }

  async function handleUpload(file) {
    try {
      const created = await uploadIssueAttachment(issueId, file);
      setAttachments((current) => [...current, created]);
      toast.success("Attachment uploaded.");
    } catch (err) {
      toast.error(err.message || "Unable to upload attachment.");
      throw err;
    }
  }

  async function handleDeleteAttachment(attachment) {
    const confirmed = window.confirm(
      `Delete "${attachment.filename || "this attachment"}"?`
    );
    if (!confirmed) return;

    try {
      await deleteIssueAttachment(attachment.id);
      setAttachments((current) =>
        current.filter((item) => item.id !== attachment.id)
      );
      toast.success("Attachment deleted.");
    } catch (err) {
      toast.error(err.message || "Unable to delete attachment.");
    }
  }

  function openEditModal() {
    setEditForm({
      title: issue.title || "",
      description: issue.description || "",
      issue_type: issue.issue_type || "task",
      priority: issue.priority || "medium",
    });
    setEditOpen(true);
  }

  async function handleUpdateIssue(event) {
    event.preventDefault();
    if (!isWorkspaceAdmin || isReadOnly || saving) return;

    setSaving(true);
    try {
      const updated = await updateIssue(issue.id, editForm);
      setIssue((current) => ({ ...current, ...updated }));
      setEditOpen(false);
      toast.success("Issue updated.");
    } catch (err) {
      toast.error(err.message || "Unable to update issue.");
    } finally {
      setSaving(false);
    }
  }

  function handleDeleteIssue() {
    if (!isWorkspaceAdmin || isReadOnly) return;
    setDeleteOpen(true);
  }

  async function confirmDeleteIssue() {
    if (!isWorkspaceAdmin || isReadOnly || saving) return;

    setSaving(true);
    try {
      await deleteIssue(issue.id);
      setDeleteOpen(false);
      toast.success("Issue deleted.");
      navigate(project?.id ? `/projects/${project.id}` : "/projects");
    } catch (err) {
      toast.error(err.message || "Unable to delete issue.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCompletionToggle() {
    if (!isWorkspaceAdmin || project?.status === "completed" || workflowBusy) return;

    const targetStatus = issueCompleted
      ? workflowStatuses.find((item) => item.is_default && !item.is_completed)
        || workflowStatuses.find((item) => !item.is_completed)
      : workflowStatuses.find((item) => item.is_completed);

    if (!targetStatus) {
      toast.error(
        issueCompleted
          ? "No active workflow status is configured."
          : "No completed workflow status is configured."
      );
      return;
    }

    setWorkflowBusy(true);
    try {
      await moveIssue(issue.id, {
        status: targetStatus.slug,
        position: issue.position || 0,
      });
      await loadIssue(true);
      toast.success(issueCompleted ? "Issue reopened." : "Issue completed.");
    } catch (err) {
      toast.error(err.message || "Unable to change issue completion.");
    } finally {
      setWorkflowBusy(false);
    }
  }

  function canDeleteAttachment(attachment) {
    const uploader = String(attachment.uploaded_by || "").trim().toLowerCase();
    const identity = [user?.username, user?.email]
      .filter(Boolean)
      .map((value) => String(value).trim().toLowerCase());

    return !isReadOnly && (isWorkspaceAdmin || identity.includes(uploader));
  }

  if (workspaceLoading || loading || (issue && !issueMatchesSelectedWorkspace)) {
    return <main className="container issue-details-page"><Loader text="Loading issue..." /></main>;
  }

  if (error || !issue) {
    return (
      <main className="container issue-details-page">
        <div className="issue-error-state">
          <h1>Unable to open this issue</h1>
          <p>{error || "The issue may have been removed or you may not have access to it."}</p>
          <button className="issue-action-button issue-action-secondary" onClick={() => navigate(project?.id ? `/projects/${project.id}` : "/projects")}>
            Back to board
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="container issue-details-page">
      <div className="issue-page-toolbar">
        <span className="projects-eyebrow">WORK ITEM DETAILS</span>
        <button
          type="button"
          className="issue-refresh-button"
          onClick={() => loadIssue(true)}
          disabled={refreshing}
        >
          <RefreshCw size={15} className={refreshing ? "issue-spin" : ""} />
          Refresh
        </button>
      </div>

      {isWorkspaceAdmin && (
        <div className="issue-management-toolbar">
          {issueCompleted && (
            <span className="issue-completed-badge">
              <CheckCircle2 size={15} /> Completed
            </span>
          )}
          {!isReadOnly && (
            <>
              <button
                type="button"
                className="issue-action-button issue-action-secondary"
                onClick={openEditModal}
              >
                <Pencil size={15} /> Edit issue
              </button>
              <button
                type="button"
                className="issue-action-button issue-action-danger"
                onClick={handleDeleteIssue}
              >
                <Trash2 size={15} /> Delete
              </button>
            </>
          )}
          {project?.status !== "completed" && (
            <button
              type="button"
              className="issue-action-button issue-action-primary"
              onClick={handleCompletionToggle}
              disabled={workflowBusy}
            >
              {issueCompleted ? <RotateCcw size={15} /> : <CheckCircle2 size={15} />}
              {workflowBusy
                ? "Updating..."
                : issueCompleted ? "Reopen issue" : "Complete issue"}
            </button>
          )}
        </div>
      )}

      <IssueDetailsPanel
        issue={issue}
        project={project}
        readOnly={isReadOnly}
      />

      {issueCompleted && (
        <p className="issue-readonly-note issue-completed-notice">
          This issue is completed. Discussion and attachments are read-only
          until a workspace owner or admin reopens it.
        </p>
      )}

      <div className="issue-details-lower-grid">
        <section className="issue-section-card">
          <header className="issue-section-heading">
            <div>
              <span className="issue-section-icon"><MessageSquare size={17} /></span>
              <div>
                <h2>Discussion</h2>
                <p>{comments.length} {comments.length === 1 ? "comment" : "comments"}</p>
              </div>
            </div>
          </header>
          <CommentList comments={comments} />
          <div className="issue-section-divider" />
          <CommentForm onSubmit={handleComment} disabled={isReadOnly} />
          {isReadOnly && (
            <p className="issue-readonly-note">This project is completed. Existing comments are available, but new comments are disabled.</p>
          )}
        </section>

        <section className="issue-section-card">
          <header className="issue-section-heading">
            <div>
              <span className="issue-section-icon"><Paperclip size={17} /></span>
              <div>
                <h2>Attachments</h2>
                <p>{attachments.length} {attachments.length === 1 ? "file" : "files"}</p>
              </div>
            </div>
          </header>
          <AttachmentList
            attachments={attachments}
            canDelete={canDeleteAttachment}
            onDelete={handleDeleteAttachment}
          />
          <div className="issue-section-divider" />
          <AttachmentUploader onUpload={handleUpload} disabled={isReadOnly} />
          {isReadOnly && (
            <p className="issue-readonly-note">This project is completed. Files remain available for viewing, but uploads and deletions are disabled.</p>
          )}
        </section>
      </div>

      <Modal
        open={editOpen}
        onClose={() => !saving && setEditOpen(false)}
        titleId="edit-issue-title"
        size="large"
      >
        <div className="issue-dialog-content">
          <span className="projects-eyebrow">ISSUE MANAGEMENT</span>
          <h2 id="edit-issue-title">Edit issue</h2>
          <p className="issue-dialog-description">
            Update the details of this work item.
          </p>

          <form className="issue-edit-form-grid" onSubmit={handleUpdateIssue}>
            <label>
              <span>Issue title</span>
              <input
                value={editForm.title}
                onChange={(event) =>
                  setEditForm((current) => ({ ...current, title: event.target.value }))
                }
                required
                maxLength={255}
                autoFocus
              />
            </label>

            <label>
              <span>Description</span>
              <textarea
                rows={5}
                value={editForm.description}
                onChange={(event) =>
                  setEditForm((current) => ({ ...current, description: event.target.value }))
                }
              />
            </label>

            <div className="issue-edit-form-row">
              <label>
                <span>Issue type</span>
                <div className="members-role-dropdown issue-field-dropdown">
                  <button
                    type="button"
                    className={`members-role-trigger ${issueTypeOpen ? "is-open" : ""}`}
                    onClick={() => {
                      setIssueTypeOpen((open) => !open);
                      setPriorityOpen(false);
                    }}
                    aria-expanded={issueTypeOpen}
                    aria-haspopup="listbox"
                  >
                    <span>{{"task":"Task","bug":"Bug","story":"Task","epic":"Task"}[editForm.issue_type] || "Task"}</span>
                    <ChevronDown size={17} />
                  </button>
                  {issueTypeOpen && (
                    <div className="members-role-menu" role="listbox" aria-label="Issue type">
                      {[
                        { value: "task", label: "Task" },
                        { value: "bug", label: "Bug" },
                      ].map((option) => (
                        <button
                          type="button"
                          role="option"
                          aria-selected={editForm.issue_type === option.value}
                          key={option.value}
                          className={`members-role-option ${editForm.issue_type === option.value ? "selected" : ""}`}
                          onClick={() => {
                            setEditForm((current) => ({ ...current, issue_type: option.value }));
                            setIssueTypeOpen(false);
                          }}
                        >
                          <span>{option.label}</span>
                          {editForm.issue_type === option.value && <Check size={16} />}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </label>

              <label>
                <span>Priority</span>
                <div className="members-role-dropdown issue-field-dropdown">
                  <button
                    type="button"
                    className={`members-role-trigger ${priorityOpen ? "is-open" : ""}`}
                    onClick={() => {
                      setPriorityOpen((open) => !open);
                      setIssueTypeOpen(false);
                    }}
                    aria-expanded={priorityOpen}
                    aria-haspopup="listbox"
                  >
                    <span>{{"low":"Low","medium":"Medium","high":"High","urgent":"Urgent"}[editForm.priority] || "Medium"}</span>
                    <ChevronDown size={17} />
                  </button>
                  {priorityOpen && (
                    <div className="members-role-menu" role="listbox" aria-label="Priority">
                      {[
                        { value: "low", label: "Low" },
                        { value: "medium", label: "Medium" },
                        { value: "high", label: "High" },
                        { value: "urgent", label: "Urgent" },
                      ].map((option) => (
                        <button
                          type="button"
                          role="option"
                          aria-selected={editForm.priority === option.value}
                          key={option.value}
                          className={`members-role-option ${editForm.priority === option.value ? "selected" : ""}`}
                          onClick={() => {
                            setEditForm((current) => ({ ...current, priority: option.value }));
                            setPriorityOpen(false);
                          }}
                        >
                          <span>{option.label}</span>
                          {editForm.priority === option.value && <Check size={16} />}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </label>
            </div>

            <div className="issue-dialog-actions">
              <button
                type="button"
                className="issue-dialog-cancel"
                onClick={() => setEditOpen(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="issue-dialog-save"
                disabled={saving || !editForm.title.trim()}
              >
                {saving ? "Saving..." : "Save changes"}
              </button>
            </div>
          </form>
        </div>
      </Modal>

      <Modal
        open={deleteOpen}
        onClose={() => !saving && setDeleteOpen(false)}
        titleId="delete-issue-title"
        size="small"
      >
        <div className="issue-dialog-content issue-delete-dialog">
          <span className="issue-delete-icon"><Trash2 size={23} /></span>
          <h2 id="delete-issue-title">Delete this issue?</h2>
          <p className="issue-dialog-description">
            You're about to permanently delete <strong>{issue.title}</strong>.
            This action cannot be undone.
          </p>
          <div className="issue-dialog-actions">
            <button
              type="button"
              className="issue-dialog-cancel"
              onClick={() => setDeleteOpen(false)}
              disabled={saving}
            >
              Keep issue
            </button>
            <button
              type="button"
              className="issue-dialog-delete"
              onClick={confirmDeleteIssue}
              disabled={saving}
            >
              {saving ? "Deleting..." : "Delete issue"}
            </button>
          </div>
        </div>
      </Modal>
    </main>
  );
}
