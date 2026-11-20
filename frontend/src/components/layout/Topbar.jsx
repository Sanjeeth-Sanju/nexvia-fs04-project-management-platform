import { Menu, Shield } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import NotificationCenter from "../../features/notifications/NotificationCenter";

function Topbar({ onMenuClick }) {
  const { user } = useAuth();
  const { selectedWorkspace } = useWorkspace();

  const displayName =
    user?.display_name || user?.username || user?.email || "Your account";

  const initials =
    displayName
      .split(/[\s@._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join("") || "U";

  const organizationName = selectedWorkspace?.name || "No workspace";
  const workspaceRole = selectedWorkspace?.current_user_role;

  return (
    <header className="app-topbar">
      <div className="topbar-heading">
        <button
          type="button"
          className="topbar-menu-button"
          onClick={onMenuClick}
          aria-label="Open navigation"
        >
          <Menu size={21} />
        </button>

        <div className="topbar-workspace-identity">
          <h1 className="topbar-workspace-title">
            {organizationName}
          </h1>

          {workspaceRole && (
            <span className={`member-role role-${workspaceRole}`}>
              <Shield size={13} />
              {workspaceRole.charAt(0).toUpperCase() + workspaceRole.slice(1)}
            </span>
          )}
        </div>
      </div>

      <div className="topbar-actions">
        <NotificationCenter />

        <div className="topbar-profile">
          <div className="topbar-avatar">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" />
            ) : (
              initials
            )}
          </div>

          <div className="topbar-profile-info">
            <span>{displayName}</span>
            <small>Account</small>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Topbar;
