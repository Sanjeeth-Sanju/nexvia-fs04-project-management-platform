import BoardSelect from "./BoardSelect";
import { Search, Plus } from "lucide-react";

export default function BoardToolbar({
  projects,
  selectedProjectId,
  onProjectChange,
  search,
  onSearchChange,
  onCreateIssue,
  showProjectSelect = true,
}) {
  return (
    <div className="kanban-toolbar">
      {showProjectSelect && (
        <BoardSelect
          label="Select project"
          value={selectedProjectId || ""}
          onChange={onProjectChange}
          options={[
            ...projects.map((project) => ({
              value: String(project.id),
              label: project.name,
            })),
          ]}
          className="kanban-project-select"
        />
      )}

      <div className="kanban-toolbar-search">
        <Search size={16} />
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search issues..."
        />
      </div>

      {onCreateIssue && (
        <button
          type="button"
          className="kanban-primary-button"
          onClick={onCreateIssue}
          disabled={!selectedProjectId}
        >
          <Plus size={16} />
          Create issue
        </button>
      )}
    </div>
  );
}
