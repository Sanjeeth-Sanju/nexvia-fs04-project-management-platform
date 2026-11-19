import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  CircleDot,
  Flag,
  Folder,
  UserRound,
} from "lucide-react";
import { Link } from "react-router-dom";

const priorityLabels = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

const typeLabels = {
  task: "Task",
  bug: "Bug",
  story: "Task",
  epic: "Task",
};

const statusLabels = {
  todo: "To do",
  in_progress: "In progress",
  done: "Done",
};

export default function IssueDetailsPanel({ issue, project, readOnly }) {
  return (
    <section className="issue-details-card">
      <div className="issue-details-breadcrumbs">
        <Link to={`/board?project=${project?.id || issue.project}`}>
          <ArrowLeft size={15} /> Back to board
        </Link>
        <span>/</span>
        <span>{project?.key || "Project"}</span>
        <span>/</span>
        <span>Issue #{issue.id}</span>
      </div>

      <div className="issue-details-heading">
        <div className="issue-details-heading-copy">
          <div className="issue-details-kicker">
            <span>{project?.key || "ISSUE"}-{issue.id}</span>
            {readOnly && (
              <span className="issue-readonly-label">
                <CheckCircle2 size={13} /> Completed project · Read only
              </span>
            )}
          </div>
          <h1>{issue.title}</h1>
          {project?.name && (
            <p className="issue-project-name">
              <Folder size={15} /> {project.name}
            </p>
          )}
        </div>
      </div>

      <div className="issue-details-description">
        <h2>Description</h2>
        {issue.description?.trim() ? (
          <p>{issue.description}</p>
        ) : (
          <p className="issue-muted">No description has been added.</p>
        )}
      </div>

      <div className="issue-details-properties">
        <div>
          <span><CircleDot size={14} /> Status</span>
          <strong>{statusLabels[issue.status] || issue.status || "—"}</strong>
        </div>
        <div>
          <span><Flag size={14} /> Priority</span>
          <strong className={`issue-priority-value issue-priority-${issue.priority}`}>
            {priorityLabels[issue.priority] || issue.priority || "—"}
          </strong>
        </div>
        <div>
          <span><UserRound size={14} /> Assignee</span>
          <strong>{issue.assignee_name || issue.assignee_username || "Unassigned"}</strong>
        </div>
        <div>
          <span><CalendarDays size={14} /> Created</span>
          <strong>
            {issue.created_at
              ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(issue.created_at))
              : "—"}
          </strong>
        </div>
        <div>
          <span><Folder size={14} /> Type</span>
          <strong>{typeLabels[issue.issue_type] || issue.issue_type || "—"}</strong>
        </div>
      </div>
    </section>
  );
}
