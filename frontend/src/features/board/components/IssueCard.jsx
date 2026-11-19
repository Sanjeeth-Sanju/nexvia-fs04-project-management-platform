import { CalendarDays, MessageSquare, GripVertical } from "lucide-react";

export default function IssueCard({
  issue,
  onDragStart,
  onDrop,
  onClick,
  readOnly = false,
}) {
  const priorityColors = {
    low: "#64748b",
    medium: "#2563eb",
    high: "#d97706",
    critical: "#dc2626",
  };

  return (
    <article
      className="kanban-issue-card"
      draggable={!readOnly}
      onDragStart={readOnly ? undefined : (event) => onDragStart(event, issue)}
      onDragOver={readOnly ? undefined : (event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
      }}
      onDrop={readOnly ? undefined : (event) => {
        event.preventDefault();
        event.stopPropagation();
        onDrop?.(event);
      }}
      onClick={() => onClick(issue)}
    >
      <div className="kanban-issue-card-top">
        <span className="kanban-issue-key">
          {issue.project_key || `ISSUE-${issue.id}`}
        </span>
        {!readOnly && <GripVertical size={15} />}
      </div>

      <h3>{issue.title}</h3>

      {issue.description && (
        <p className="kanban-issue-description">{issue.description}</p>
      )}

      <div className="kanban-issue-card-footer">
        <span
          className="kanban-priority"
          style={{ color: priorityColors[issue.priority] || "#64748b" }}
        >
          <span style={{ background: priorityColors[issue.priority] || "#64748b" }} />
          {issue.priority}
        </span>

        <div className="kanban-issue-meta">
          {issue.due_date && <CalendarDays size={14} />}
          {issue.assignee_name && (
            <span className="kanban-assignee">
              {issue.assignee_name.slice(0, 2).toUpperCase()}
            </span>
          )}
        </div>
      </div>
    </article>
  );
}
