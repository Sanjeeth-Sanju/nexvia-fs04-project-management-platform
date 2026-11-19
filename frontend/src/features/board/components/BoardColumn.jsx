import { Plus } from "lucide-react";
import IssueCard from "./IssueCard";

export default function BoardColumn({
  status,
  issues,
  onDrop,
  onDragStart,
  onIssueClick,
  onAddIssue,
  readOnly = false,
}) {
  return (
    <section
      className="kanban-column"
      onDragOver={(event) => {
        if (!readOnly) event.preventDefault();
      }}
      onDrop={(event) => {
        if (!readOnly) onDrop(event, status, null);
      }}
    >
      <header className="kanban-column-header">
        <div>
          <span className="kanban-status-dot" />
          <h2>{status.name}</h2>
          <span className="kanban-column-count">{issues.length}</span>
        </div>

        {!readOnly && (
          <button
            type="button"
            className="kanban-icon-button"
            onClick={() => onAddIssue(status.slug)}
            title={`Add issue to ${status.name}`}
            aria-label={`Add issue to ${status.name}`}
          >
            <Plus size={17} />
          </button>
        )}
      </header>

      <div className="kanban-column-content">
        {issues.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            onDragStart={onDragStart}
            onDrop={(event) => onDrop(event, status, issue)}
            onClick={onIssueClick}
            readOnly={readOnly}
          />
        ))}

        {issues.length === 0 && (
          <div className="kanban-column-empty">
            {readOnly ? "No issues in this status" : "Drop issues here"}
          </div>
        )}
      </div>
    </section>
  );
}
