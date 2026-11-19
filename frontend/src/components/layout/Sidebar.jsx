import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Building2,
  FolderKanban,
  Users,
  Activity,
  Settings,
  CreditCard,
  ChevronDown,
  LogOut,
  Check,
} from "lucide-react";

import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { ROUTES } from "../../constants/routes";
import { apiRequest } from "../../services/api";
import PlanUpgradeModal from "./PlanUpgradeModal";

const mainNavigation = [
  {
    label: "Overview",
    items: [
      { name: "Dashboard", path: ROUTES.DASHBOARD, icon: LayoutDashboard },
      { name: "Workspaces", path: ROUTES.WORKSPACES, icon: Building2 },
      { name: "Projects", path: ROUTES.PROJECTS, icon: FolderKanban },
      { name: "Members", path: ROUTES.MEMBERS, icon: Users },
      { name: "Activity", path: ROUTES.ACTIVITY, icon: Activity },
    ],
  },
];

const secondaryNavigation = [
  { name: "Settings", path: ROUTES.SETTINGS, icon: Settings },
  { name: "Billing", path: ROUTES.BILLING, icon: CreditCard },
];

function Sidebar({ onNavigate }) {
  const { user, logout } = useAuth();

  const {
    workspaces,
    selectedWorkspace,
    selectedWorkspaceId,
    selectWorkspace,
    loading: workspacesLoading,
    error: workspaceError,
  } = useWorkspace();

  const navigate = useNavigate();
  const location = useLocation();
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [accountPlan, setAccountPlan] = useState("free");
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  useEffect(() => {
    const openUpgrade = () => setUpgradeOpen(true);
    window.addEventListener("billing:upgrade-required", openUpgrade);
    return () => window.removeEventListener("billing:upgrade-required", openUpgrade);
  }, []);

  useEffect(() => {
    let active = true;

    apiRequest("/billing/overview/")
      .then((overview) => {
        if (active) setAccountPlan(overview?.plan || "free");
      })
      .catch(() => {
        if (active) setAccountPlan("free");
      });

    return () => {
      active = false;
    };
  }, []);

  // Remember the last page visited inside the Projects section.
  // This includes project details and issue details.
  const lastProjectsRoute = useRef(ROUTES.PROJECTS);
  const lastWorkspaceId = useRef(selectedWorkspaceId);

  useEffect(() => {
    if (String(lastWorkspaceId.current) !== String(selectedWorkspaceId)) {
      lastWorkspaceId.current = selectedWorkspaceId;
      lastProjectsRoute.current = ROUTES.PROJECTS;
    }
  }, [selectedWorkspaceId]);

  useEffect(() => {
    const pathname = location.pathname;
    const isProjectsSection =
      pathname.startsWith("/projects/") ||
      pathname.startsWith("/issues/");

    if (isProjectsSection) {
      lastProjectsRoute.current =
        `${location.pathname}${location.search}${location.hash}`;
    }
  }, [location.pathname, location.search, location.hash]);

  const displayName =
    user?.display_name || user?.username || user?.email || "Your account";
  const initials = displayName
    .split(/[\\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "U";

  async function handleLogout() {
    try {
      await logout();
      navigate(ROUTES.LOGIN, { replace: true });
    } catch (error) {
      console.error("Logout failed:", error);
    }
  }

  function handleWorkspaceSelect(workspaceId) {
    const changed = String(workspaceId) !== String(selectedWorkspaceId);
    setWorkspaceOpen(false);

    if (!changed) return;

    lastProjectsRoute.current = ROUTES.PROJECTS;
    lastWorkspaceId.current = String(workspaceId);

    selectWorkspace(workspaceId);
    navigate(ROUTES.DASHBOARD, { replace: true });
  }

  return (
    <aside className="app-sidebar">
      <div
        className="sidebar-brand"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
        }}
      >
        <span>NEXVIA</span>
        <button
          type="button"
          onClick={() => setUpgradeOpen(true)}
          title="View your subscription plan"
          aria-label={`Current plan: ${accountPlan}. Open billing`}
          style={{
            border: "1px solid var(--color-border)",
            borderRadius: "999px",
            padding: "5px 10px",
            background:
              accountPlan === "business"
                ? "var(--color-primary-dark)"
                : accountPlan === "pro"
                  ? "var(--color-soft-green)"
                  : "var(--color-surface)",
            color:
              accountPlan === "business"
                ? "#FFFFFF"
                : "var(--color-primary-dark)",
            fontFamily: "var(--font-body)",
            fontSize: "10px",
            fontWeight: 700,
            letterSpacing: "0.08em",
            cursor: "pointer",
            lineHeight: 1.2,
          }}
        >
          {accountPlan.toUpperCase()}
        </button>
      </div>

      <div className="sidebar-workspace">
        <button
          type="button"
          className="workspace-switcher"
          onClick={() => setWorkspaceOpen((previous) => !previous)}
          aria-expanded={workspaceOpen}
          aria-label="Select workspace"
        >
          <div className="workspace-icon">
            <Building2 size={18} />
          </div>

          <div className="workspace-info">
            <span className="workspace-label">WORKSPACE</span>
            <span className="workspace-name">
              {workspacesLoading
                ? "Loading..."
                : selectedWorkspace?.name || "No workspace"}
            </span>
          </div>

          <ChevronDown
            size={16}
            className={workspaceOpen ? "workspace-chevron-open" : ""}
          />
        </button>

        {workspaceOpen && (
          <div className="workspace-dropdown">
            <p className="workspace-dropdown-title">
              Switch workspace
            </p>

            {workspacesLoading ? (
              <span>Loading workspaces...</span>
            ) : workspaceError ? (
              <span>{workspaceError}</span>
            ) : workspaces.length ? (
              <div className="workspace-options">
                {workspaces.map((workspace) => (
                  <button
                    type="button"
                    key={workspace.id}
                    className={`workspace-option ${
                      String(workspace.id) === String(selectedWorkspaceId)
                        ? "workspace-option-active"
                        : ""
                    }`}
                    onClick={() => handleWorkspaceSelect(workspace.id)}
                  >
                    <span>{workspace.name}</span>
                    {String(workspace.id) === String(selectedWorkspaceId) && (
                      <Check size={16} />
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <span>No workspaces found.</span>
            )}
          </div>
        )}
      </div>

      <nav className="sidebar-navigation" aria-label="Main navigation">
        {mainNavigation.map((section) => (
          <div className="sidebar-section" key={section.label}>
            <p className="sidebar-section-label">{section.label}</p>

            {section.items.map(({ name, path, icon: Icon }) => (
              <NavLink
                key={path}
                to={
                name === "Projects"
                  ? lastProjectsRoute.current
                  : path
              }
                end={path === ROUTES.DASHBOARD}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? "sidebar-link-active" : ""}`
                }
                onClick={onNavigate}
              >
                <Icon size={18} strokeWidth={1.9} />
                <span>{name}</span>
              </NavLink>
            ))}
          </div>
        ))}

        <div className="sidebar-section sidebar-bottom-navigation">
          <p className="sidebar-section-label">PREFERENCES</p>

          {secondaryNavigation.map(({ name, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "sidebar-link-active" : ""}`
              }
              onClick={onNavigate}
            >
              <Icon size={18} strokeWidth={1.9} />
              <span>{name}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="sidebar-user">
        <div className="user-avatar">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" />
          ) : (
            initials
          )}
        </div>

        <div className="sidebar-user-info">
          <span className="sidebar-user-name">{displayName}</span>
          <span className="sidebar-user-email">
            {user?.email || "Signed in"}
          </span>
        </div>

        <button
          type="button"
          className="sidebar-logout"
          onClick={handleLogout}
          title="Sign out"
          aria-label="Sign out"
        >
          <LogOut size={17} />
        </button>
      </div>
      {upgradeOpen && (
        <PlanUpgradeModal
          currentPlan={accountPlan}
          onClose={() => setUpgradeOpen(false)}
        />
      )}
    </aside>
  );
}

export default Sidebar;
