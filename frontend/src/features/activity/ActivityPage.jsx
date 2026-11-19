import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Clock3,
  Filter,
  RefreshCw,
  Search,
  Repeat,
  MessageCircle,
  Paperclip,
  UserPlus,
  UserMinus,
  CirclePlus,
  Pencil,
  Trash2,
  ArrowRightLeft,
  Flag,
  FolderKanban,
  ChevronLeft,
  ChevronRight,
  CalendarDays,
  X,
} from "lucide-react";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useToast } from "../../context/ToastContext";
import { getWorkspaceActivity } from "./activityService";
import BoardSelect from "../board/components/BoardSelect";
import { useNavigationPageState } from "../../components/layout/AppLayout";

const PAGE_SIZE = 20;

// ACTIVITY_FILTERS_PAGINATION_V1
const labels = {
  "issue.created": "created an issue",
  "issue.updated": "updated an issue",
  "issue.deleted": "deleted an issue",
  "issue.moved": "moved an issue",
  "issue.comment.created": "commented on an issue",
  "issue.comment.updated": "edited an issue comment",
  "issue.comment.deleted": "deleted an issue comment",
  "issue.attachment.created": "uploaded an attachment",
  "issue.attachment.deleted": "deleted an attachment",
  "sprint.created": "created a sprint",
  "sprint.updated": "updated a sprint",
  "sprint.completed": "completed a sprint",
  "sprint.reopened": "reopened a sprint",
  "project.created": "created a project",
  "project.updated": "updated a project",
  "project.deleted": "deleted a project",
  "project.completed": "completed a project",
  "project.reopened": "reopened a project",
  "workflow_status.created": "created a workflow status",
  "workflow_status.updated": "updated a workflow status",
  "workflow_status.deleted": "deleted a workflow status",
  "workspace.member_added": "added",
  "workspace.member_removed": "removed",
  "workspace.member_role_changed": "changed the role of",
};

const title = (item) => {
  const details = item.details || {};

  if (item.action === "issue.comment.created" ||
      item.action === "issue.comment.updated" ||
      item.action === "issue.comment.deleted" ||
      item.action === "issue.attachment.created" ||
      item.action === "issue.attachment.deleted") {
    return details.issue_title || "an issue";
  }

  if (item.action === "workspace.member_added") {
    return `${details.member_name || details.member_email || "A member"} to the workspace`;
  }

  if (item.action === "workspace.member_removed") {
    return `${details.member_name || details.member_email || details.email || "A member"} from the workspace`;
  }

  if (item.action === "workspace.member_role_changed") {
    const member =
      details.member_name ||
      details.member_email ||
      details.email ||
      (details.user_id ? `Member #${details.user_id}` : "a member");

    const oldRole = details.old_role;
    const newRole = details.new_role;

    const roleChange =
      oldRole && newRole
        ? ` (${oldRole} → ${newRole})`
        : "";

    return `${member}${roleChange}`;
  }

  return details.title ||
    details.name ||
    details.project_name ||
    details.filename ||
    `${item.entity_type || "Workspace"} ${item.entity_id || ""}`;
};

const eventIcons = {
  "issue.created": CirclePlus,
  "issue.updated": Pencil,
  "issue.deleted": Trash2,
  "issue.moved": ArrowRightLeft,
  "issue.comment.created": MessageCircle,
  "issue.comment.updated": MessageCircle,
  "issue.comment.deleted": MessageCircle,
  "issue.attachment.created": Paperclip,
  "issue.attachment.deleted": Paperclip,
  "sprint.created": Flag,
  "sprint.updated": Flag,
  "sprint.completed": Flag,
  "sprint.reopened": Flag,
  "project.created": FolderKanban,
  "project.updated": FolderKanban,
  "project.deleted": FolderKanban,
  "project.completed": FolderKanban,
  "project.reopened": FolderKanban,
  "workspace.member_added": UserPlus,
  "workspace.member_removed": UserMinus,
  "workspace.member_role_changed": UserPlus,
};

const date = (value) =>
  value
    ? new Date(value).toLocaleString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "Unknown date";

const day = (value) => {
  if (!value) return "Earlier";

  const current = new Date(value);
  const today = new Date();

  if (current.toDateString() === today.toDateString()) return "Today";

  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  return current.toDateString() === yesterday.toDateString()
    ? "Yesterday"
    : current.toLocaleDateString(undefined, {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
};

const searchableProject = (item) =>
  [
    item.details?.project_name,
    item.details?.project,
    item.details?.project_id,
    item.details?.project_key,
  ]
    .filter(Boolean)
    .join(" ");


// ACTIVITY_NEXVIA_DESIGN_V2
function activityDateValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function activityDateLabel(value) {
  if (!value) return "Any date";
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function ActivityDatePicker({ label, value, onChange, min, max }) {
  const [open, setOpen] = useState(false);
  const [visibleMonth, setVisibleMonth] = useState(() => {
    const initial = value ? new Date(`${value}T00:00:00`) : new Date();
    return new Date(initial.getFullYear(), initial.getMonth(), 1);
  });

  useEffect(() => {
    if (!open) return;

    const closeOutside = (event) => {
      if (!event.target.closest(".activity-date-picker")) setOpen(false);
    };
    const closeEscape = (event) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", closeOutside);
    document.addEventListener("keydown", closeEscape);

    return () => {
      document.removeEventListener("mousedown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [open]);

  useEffect(() => {
    if (!value) return;
    const selected = new Date(`${value}T00:00:00`);
    setVisibleMonth(new Date(selected.getFullYear(), selected.getMonth(), 1));
  }, [value]);

  const year = visibleMonth.getFullYear();
  const month = visibleMonth.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const dayCount = new Date(year, month + 1, 0).getDate();
  const monthLabel = visibleMonth.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });

  const cells = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: dayCount }, (_, index) => index + 1),
  ];
  while (cells.length % 7) cells.push(null);

  return (
    <div className="activity-date-picker">
      <span className="activity-filter-label">{label}</span>

      <button
        type="button"
        className={`sprint-date-trigger${open ? " is-open" : ""}`}
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <CalendarDays size={16} />
        <span>{activityDateLabel(value)}</span>
        <ChevronRight size={15} />
      </button>

      {open && (
        <div className="sprint-calendar" role="dialog" aria-label={label}>
          <div className="sprint-calendar__header">
            <button
              type="button"
              onClick={() => setVisibleMonth(new Date(year, month - 1, 1))}
              aria-label="Previous month"
            >
              <ChevronLeft size={17} />
            </button>

            <strong>{monthLabel}</strong>

            <button
              type="button"
              onClick={() => setVisibleMonth(new Date(year, month + 1, 1))}
              aria-label="Next month"
            >
              <ChevronRight size={17} />
            </button>
          </div>

          <div className="sprint-calendar__grid">
            {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => (
              <span className="sprint-calendar__weekday" key={day}>
                {day}
              </span>
            ))}

            {cells.map((day, index) => {
              if (!day) return <span key={`blank-${index}`} />;

              const iso = activityDateValue(new Date(year, month, day));
              const disabled = Boolean(
                (min && iso < min) || (max && iso > max)
              );

              return (
                <button
                  type="button"
                  key={iso}
                  disabled={disabled}
                  className={iso === value ? "selected" : ""}
                  aria-pressed={iso === value}
                  onClick={() => {
                    onChange(iso);
                    setOpen(false);
                  }}
                >
                  {day}
                </button>
              );
            })}
          </div>

          <div className="sprint-calendar__footer">
            <button
              type="button"
              onClick={() => {
                onChange("");
                setOpen(false);
              }}
            >
              Clear date
            </button>

            <button
              type="button"
              onClick={() => {
                const today = activityDateValue(new Date());
                if ((!min || today >= min) && (!max || today <= max)) {
                  onChange(today);
                }
                setOpen(false);
              }}
            >
              Today
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ACTIVITY_ENTITY_ICON_AND_FILTER_V2
// ACTIVITY_SPRINT_REPEAT_ICON_V1
export default function ActivityPage() {
  const { selectedWorkspace, selectedWorkspaceId } = useWorkspace();
  const toast = useToast();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [activityState, setActivityState] = useNavigationPageState(
    "activity",
    {
      query: "",
      kind: "all",
      projectQuery: "",
      memberQuery: "",
      dateFrom: "",
      dateTo: "",
      page: 1,
    }
  );

  const {
    query,
    kind,
    projectQuery,
    memberQuery,
    dateFrom,
    dateTo,
    page,
  } = activityState;

  const updateActivityField = (field) => (value) => {
    setActivityState((current) => ({
      ...current,
      [field]:
        typeof value === "function"
          ? value(current[field])
          : value,
    }));
  };

  const setQuery = updateActivityField("query");
  const setKind = updateActivityField("kind");
  const setProjectQuery = updateActivityField("projectQuery");
  const setMemberQuery = updateActivityField("memberQuery");
  const setDateFrom = updateActivityField("dateFrom");
  const setDateTo = updateActivityField("dateTo");
  const setPage = updateActivityField("page");

  const previousFilters = useRef({
    query,
    kind,
    projectQuery,
    memberQuery,
    dateFrom,
    dateTo,
  });

  const load = useCallback(
    async (quiet) => {
      if (!selectedWorkspaceId) {
        setItems([]);
        setLoading(false);
        return;
      }

      quiet ? setRefreshing(true) : setLoading(true);

      try {
        setItems(await getWorkspaceActivity(selectedWorkspaceId));
      } catch (error) {
        toast.error(error.message || "Unable to load activity.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selectedWorkspaceId, toast]
  );

  useEffect(() => {
    load(false);
  }, [load]);

  useEffect(() => {
    const currentFilters = {
      query,
      kind,
      projectQuery,
      memberQuery,
      dateFrom,
      dateTo,
    };

    const previous = previousFilters.current;
    const changed = Object.keys(currentFilters).some(
      (key) => currentFilters[key] !== previous[key]
    );

    if (changed) setPage(1);
    previousFilters.current = currentFilters;
  }, [query, kind, projectQuery, memberQuery, dateFrom, dateTo]);

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();
    const projectSearch = projectQuery.trim().toLowerCase();
    const memberSearch = memberQuery.trim().toLowerCase();

    const from = dateFrom ? new Date(`${dateFrom}T00:00:00`) : null;
    const to = dateTo ? new Date(`${dateTo}T23:59:59.999`) : null;

    return items.filter((item) => {
      const action = String(item.action || "");
      const timestamp = item.created_at ? new Date(item.created_at) : null;

      const matchesKind =
        kind === "all" ||
        (kind === "issues" && action.startsWith("issue.")) ||
        (kind === "projects" && action.startsWith("project.")) ||
        (kind === "sprints" && action.startsWith("sprint.")) ||
        (kind === "members" && action.startsWith("workspace.member_"));

      const matchesSearch =
        !search ||
        [
          action,
          item.actor,
          item.entity_type,
          title(item),
          JSON.stringify(item.details || {}),
        ]
          .join(" ")
          .toLowerCase()
          .includes(search);

      const matchesProject =
        !projectSearch ||
        searchableProject(item).toLowerCase().includes(projectSearch);

      const matchesMember =
        !memberSearch ||
        String(item.actor || "").toLowerCase().includes(memberSearch);

      const matchesFrom =
        !from || (timestamp && timestamp >= from);

      const matchesTo =
        !to || (timestamp && timestamp <= to);

      return (
        matchesKind &&
        matchesSearch &&
        matchesProject &&
        matchesMember &&
        matchesFrom &&
        matchesTo
      );
    });
  }, [
    items,
    query,
    kind,
    projectQuery,
    memberQuery,
    dateFrom,
    dateTo,
  ]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);

  const paginated = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, currentPage]);

  const groups = useMemo(() => {
    const grouped = new Map();

    paginated.forEach((item) => {
      const label = day(item.created_at);

      if (!grouped.has(label)) grouped.set(label, []);
      grouped.get(label).push(item);
    });

    return [...grouped];
  }, [paginated]);

  const clearFilters = () => {
    setQuery("");
    setKind("all");
    setProjectQuery("");
    setMemberQuery("");
    setDateFrom("");
    setDateTo("");
  };

  const hasFilters =
    query ||
    kind !== "all" ||
    projectQuery ||
    memberQuery ||
    dateFrom ||
    dateTo;

  return (
    <main className="container phase2-page">
      <header className="phase2-page-header">
        <div>
          <p className="phase2-eyebrow">WORKSPACE INSIGHTS</p>
          <h1>Activity</h1>
          <p className="phase2-description">
            A timeline of the work happening across{" "}
            {selectedWorkspace?.name || "your workspace"}.
          </p>
        </div>

        <button
          className="phase2-button phase2-button--secondary"
          onClick={() => load(true)}
          disabled={loading || refreshing}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </header>

      <section className="phase2-toolbar">
        <div className="phase2-search">
          <Search size={17} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search activity…"
          />
        </div>

        <div className="activity-kind-filter">
          <Filter size={16} />
          <BoardSelect
            value={kind}
            onChange={setKind}
            label="Filter activity"
            options={[
              { value: "all", label: "All activity" },
              { value: "issues", label: "Issues" },
              { value: "projects", label: "Projects" },
              { value: "sprints", label: "Sprints" },
              { value: "members", label: "Members" },
            ]}
          />
        </div>

        <span className="phase2-result-count">
          {filtered.length} events
        </span>
      </section>

      <section className="activity-filters" aria-label="Advanced activity filters">
        <label className="activity-filter-field">
          <span className="activity-filter-label">Project</span>
          <input
            className="activity-filter-input"
            value={projectQuery}
            onChange={(event) => setProjectQuery(event.target.value)}
            placeholder="Search projects"
            aria-label="Filter by project"
          />
        </label>

        <label className="activity-filter-field">
          <span className="activity-filter-label">Member</span>
          <input
            className="activity-filter-input"
            value={memberQuery}
            onChange={(event) => setMemberQuery(event.target.value)}
            placeholder="Search members"
            aria-label="Filter by member"
          />
        </label>

        <ActivityDatePicker
          label="From date"
          value={dateFrom}
          onChange={setDateFrom}
          max={dateTo || undefined}
        />

        <ActivityDatePicker
          label="To date"
          value={dateTo}
          onChange={setDateTo}
          min={dateFrom || undefined}
        />

        {hasFilters && (
          <button
            type="button"
            className="activity-clear-filters"
            onClick={clearFilters}
          >
            <X size={15} />
            Clear filters
          </button>
        )}
      </section>

      {loading ? (
        <div className="phase2-state">Loading activity…</div>
      ) : !selectedWorkspaceId ? (
        <div className="phase2-state">
          Select a workspace to view activity.
        </div>
      ) : !filtered.length ? (
        <div className="phase2-empty">
          <span className="phase2-empty-icon">
            <Activity size={24} />
          </span>
          <h2>{items.length ? "No matching activity" : "No activity yet"}</h2>
          <p>
            {items.length
              ? "Try changing your search or filters."
              : "Workspace events will appear here as your team works."}
          </p>
        </div>
      ) : (
        <>
          <div className="activity-timeline">
            {groups.map(([label, events]) => (
              <section className="activity-day" key={label}>
                <h2>{label}</h2>

                <div className="activity-day-list">
                  {events.map((item) => (
                    <article className="activity-event" key={item.id}>
                      <span className="activity-event-icon">
                        {(() => {
                          const EventIcon = eventIcons[item.action] || Activity;
                          return <EventIcon size={17} />;
                        })()}
                      </span>

                      <div className="activity-event-main">
                        <div className="activity-event-copy">
                          <strong>{item.actor || "A workspace member"}</strong>
                          <span>
                            {labels[item.action] ||
                              String(item.action || "performed an action").replace(
                                /[._]/g,
                                " "
                              )}
                          </span>
                          <b>{title(item)}</b>
                        </div>

                        <div className="activity-event-meta">
                          <span>
                            <Repeat size={13} />
                            {item.action?.startsWith("issue.attachment.")
                              ? item.details?.filename || "Attachment"
                              : item.action?.startsWith("issue.comment.")
                                ? "Comment"
                                : item.action?.startsWith("workspace.member_")
                                  ? "Workspace member"
                                  : item.entity_type || "Workspace"}
                          </span>
                          <span>
                            <Clock3 size={13} />
                            {date(item.created_at)}
                          </span>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <nav
            className="activity-pagination"
            aria-label="Activity pagination"
          >
            <span className="activity-pagination-page">
              Page {currentPage}
            </span>

            <button
              type="button"
              className="activity-pagination-button"
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={currentPage <= 1}
            >
              <ChevronLeft size={15} />
              Previous
            </button>

            <button
              type="button"
              className="activity-pagination-button"
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              disabled={currentPage >= totalPages}
            >
              Next
              <ChevronRight size={15} />
            </button>
          </nav>
        </>
      )}
    </main>
  );
}
