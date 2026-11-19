import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FolderKanban,
  ListTodo,
  Clock3,
  CheckCircle2,
  ArrowUpRight,
  RefreshCw,
} from "lucide-react";

import {
  getDashboardData,
  getWorkspaceActivity,
  getWorkspaceWorkflowStatuses,
} from "./dashboardService";
import { useWorkspace } from "../../context/WorkspaceContext";
import { ROUTES } from "../../constants/routes";

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function getInitials(value = "") {
  return value
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function getActivityDescription(activity) {
  const action = (activity.action || "").replaceAll(".", " ");
  return action || "performed an activity";
}

function DashboardPage() {
  const navigate = useNavigate();
  const { selectedWorkspace, selectedWorkspaceId, loading: workspaceLoading } = useWorkspace();

  const [dashboard, setDashboard] = useState({
    workspaces: [],
    projects: [],
    issues: [],
  });

  const [activity, setActivity] = useState([]);
  const [workflowStatuses, setWorkflowStatuses] = useState([]);

  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailsError, setDetailsError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const data = await getDashboardData();
      setDashboard(data);
    } catch (err) {
      setError(err.message || "Unable to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    if (!selectedWorkspaceId) {
      setActivity([]);
      setWorkflowStatuses([]);
      return;
    }

    let active = true;

    async function loadWorkspaceDetails() {
      setDetailsLoading(true);
      setDetailsError("");

      try {
        const [activityData, statusData] = await Promise.all([
          getWorkspaceActivity(selectedWorkspaceId),
          getWorkspaceWorkflowStatuses(selectedWorkspaceId),
        ]);

        if (active) {
          setActivity(activityData);
          setWorkflowStatuses(statusData);
        }
      } catch (err) {
        if (active) {
          setDetailsError(
            err.message || "Unable to load workspace details."
          );
          setActivity([]);
          setWorkflowStatuses([]);
        }
      } finally {
        if (active) setDetailsLoading(false);
      }
    }

    loadWorkspaceDetails();

    return () => {
      active = false;
    };
  }, [selectedWorkspaceId]);

  const workspaceProjects = useMemo(
    () =>
      dashboard.projects.filter(
        (project) =>
          String(project.workspace) === String(selectedWorkspaceId)
      ),
    [dashboard.projects, selectedWorkspaceId]
  );

  const projectIds = useMemo(
    () => new Set(workspaceProjects.map((project) => String(project.id))),
    [workspaceProjects]
  );

  const workspaceIssues = useMemo(
    () =>
      dashboard.issues.filter((issue) =>
        projectIds.has(String(issue.project))
      ),
    [dashboard.issues, projectIds]
  );

  const completedStatusSlugs = useMemo(
    () =>
      new Set(
        workflowStatuses
          .filter((status) => status.is_completed)
          .map((status) => status.slug)
      ),
    [workflowStatuses]
  );

  const completedIssues = workspaceIssues.filter((issue) =>
    completedStatusSlugs.has(issue.status)
  );

  const inProgressIssues = workspaceIssues.filter(
    (issue) => issue.status === "in_progress"
  );

  const recentIssues = [...workspaceIssues]
    .sort(
      (a, b) =>
        new Date(b.updated_at || b.created_at) -
        new Date(a.updated_at || a.created_at)
    )
    .slice(0, 5);

  const stats = [
    {
      label: "Total Projects",
      value: workspaceProjects.length,
      icon: FolderKanban,
      description: "Projects in this workspace",
      color: "green",
    },
    {
      label: "Total Issues",
      value: workspaceIssues.length,
      icon: ListTodo,
      description: "Issues across all projects",
      color: "sand",
    },
    {
      label: "In Progress",
      value: inProgressIssues.length,
      icon: Clock3,
      description: "Issues currently being worked on",
      color: "blue",
    },
    {
      label: "Completed",
      value: completedIssues.length,
      icon: CheckCircle2,
      description: "Issues in completed statuses",
      color: "purple",
    },
  ];

  if (loading || workspaceLoading) {
    return (
      <section className="dashboard-page">
        <div className="dashboard-loading">Loading your dashboard...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="dashboard-page">
        <div className="dashboard-error">
          <h2>Couldn't load your dashboard</h2>
          <p>{error}</p>
          <button type="button" onClick={loadDashboard}>
            <RefreshCw size={16} />
            Try again
          </button>
        </div>
      </section>
    );
  }

  if (!selectedWorkspace) {
    return (
      <section className="dashboard-page">
        <div className="dashboard-empty">
          <FolderKanban size={32} />
          <h2>Welcome to NEXVIA</h2>
          <p>Create or join a workspace to get your dashboard started.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="dashboard-page">
      <div className="dashboard-heading">
        <div>
          <h2>Dashboard</h2>
          <p>Your projects, issues and team activity at a glance.</p>
        </div>
      </div>

      <div className="dashboard-section-heading">
        <div>
          <h3>Workspace overview</h3>
          <p>A snapshot of your current progress.</p>
        </div>
      </div>

      <div className="dashboard-stats">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <article className="dashboard-stat-card" key={stat.label}>
              <div className={`dashboard-stat-icon ${stat.color}`}>
                <Icon size={20} />
              </div>
              <p>{stat.label}</p>
              <strong>{stat.value}</strong>
              <span>{stat.description}</span>
            </article>
          );
        })}
      </div>

      <div className="dashboard-content-grid">
        <section className="dashboard-panel dashboard-issues-panel">
          <div className="dashboard-panel-heading">
            <div>
              <h3>Recently updated issues</h3>
              <p>Your latest project activity.</p>
            </div>
            <span className="dashboard-panel-count">
              {workspaceIssues.length}
            </span>
          </div>

          {recentIssues.length ? (
            <div className="dashboard-issue-list">
              {recentIssues.map((issue) => (
                <article className="dashboard-issue-row" key={issue.id}>
                  <div className="dashboard-issue-main">
                    <span className="dashboard-issue-id">
                      #{issue.id}
                    </span>
                    <h4>{issue.title}</h4>
                    <span className="dashboard-issue-project">
                      {workspaceProjects.find(
                        (project) =>
                          String(project.id) === String(issue.project)
                      )?.name || "Project"}
                    </span>
                  </div>

                  <div className="dashboard-issue-meta">
                    <span className={`dashboard-priority ${issue.priority}`}>
                      {issue.priority}
                    </span>
                    <span className="dashboard-issue-date">
                      {formatDate(issue.updated_at || issue.created_at)}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="dashboard-panel-empty">
              <ListTodo size={24} />
              <p>No issues in this workspace yet.</p>
            </div>
          )}
        </section>

        <section className="dashboard-panel dashboard-activity-panel">
          <div className="dashboard-panel-heading">
            <div>
              <h3>Recent activity</h3>
              <p>What's been happening lately.</p>
            </div>
            <button
              type="button"
              className="dashboard-view-all"
              onClick={() => navigate(ROUTES.ACTIVITY)}
            >
              View all <ArrowUpRight size={15} />
            </button>
          </div>

          {detailsLoading ? (
            <p className="dashboard-subtle-message">Loading activity...</p>
          ) : detailsError ? (
            <p className="dashboard-subtle-message">{detailsError}</p>
          ) : activity.length ? (
            <div className="dashboard-activity-list">
              {activity.slice(0, 3).map((item) => (
                <article className="dashboard-activity-item" key={item.id}>
                  <div className="dashboard-activity-avatar">
                    {getInitials(item.actor || "System")}
                  </div>
                  <div>
                    <p>
                      <strong>{item.actor || "System"}</strong>{" "}
                      {getActivityDescription(item)}
                    </p>
                    <span>{formatDate(item.created_at)}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="dashboard-panel-empty">
              <Clock3 size={24} />
              <p>No recent activity yet.</p>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}

export default DashboardPage;
