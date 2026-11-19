import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import AuthLayout from "../auth/components/AuthLayout";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useToast } from "../../context/ToastContext";
import { ROUTES } from "../../constants/routes";
import { acceptInvitation } from "./memberService";

// Share an in-flight request across React StrictMode effect replays.
const acceptanceRequests = new Map();

function getAcceptanceRequest(token) {
  if (!acceptanceRequests.has(token)) {
    const request = acceptInvitation(token).finally(() => {
      acceptanceRequests.delete(token);
    });
    acceptanceRequests.set(token, request);
  }

  return acceptanceRequests.get(token);
}

function InvitationAcceptPage() {
  const { token } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const { isAuthenticated, loading: authLoading, logout } = useAuth();
  const { refreshWorkspaces, selectWorkspace } = useWorkspace();
  const toast = useToast();

  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (authLoading || !isAuthenticated || !token) return;

    let active = true;

    async function completeAcceptance() {
      setAccepting(true);
      setError("");

      try {
        const result = await getAcceptanceRequest(token);

        if (!active) return;

        await refreshWorkspaces();

        if (!active) return;

        if (result?.workspace_id) {
          selectWorkspace(result.workspace_id);
        }

        toast.success("You've joined the workspace successfully.");
        navigate(ROUTES.DASHBOARD, { replace: true });
      } catch (err) {
        if (active) {
          setError(
            err.message ||
              "We couldn't accept this invitation. It may have expired or belong to another email address."
          );
        }
      } finally {
        if (active) setAccepting(false);
      }
    }

    completeAcceptance();

    return () => {
      active = false;
    };
  }, [
    authLoading,
    isAuthenticated,
    token,
    refreshWorkspaces,
    selectWorkspace,
    toast,
    navigate,
  ]);

  async function handleSwitchAccount() {
    try {
      await logout();
      navigate(ROUTES.LOGIN, {
        replace: true,
        state: { from: location },
      });
    } catch {
      setError("Unable to switch accounts. Please try again.");
    }
  }

  if (authLoading) {
    return (
      <AuthLayout
        title="Checking your invitation"
        subtitle="Restoring your Nexvia session..."
      >
        <div className="page-loading">
          <p>Please wait...</p>
        </div>
      </AuthLayout>
    );
  }

  if (!isAuthenticated) {
    return (
      <AuthLayout
        title="You've been invited!"
        subtitle="You've received an invitation to collaborate on a workspace in Nexvia."
      >
        <div className="auth-form">
          <p>
            Sign in with the email address that received the invitation.
            Once you're signed in, we'll automatically add you to the workspace.
          </p>

          <Button
            fullWidth
            size="large"
            onClick={() =>
              navigate(ROUTES.LOGIN, {
                state: { from: location },
              })
            }
          >
            Sign in to accept
          </Button>

          <p className="auth-switch">
            New to Nexvia?{" "}
            <Link
              to={ROUTES.REGISTER}
              state={{ from: location }}
            >
              Create an account
            </Link>
          </p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title={error ? "Invitation couldn't be accepted" : "Joining your workspace"}
      subtitle={
        error
          ? "There was a problem accepting this invitation."
          : "Please wait while we securely add you to the workspace."
      }
    >
      <div className="auth-form">
        {error ? (
          <>
            <div className="auth-error" role="alert">
              {error}
            </div>

            <Button fullWidth size="large" onClick={handleSwitchAccount}>
              Switch account and try again
            </Button>

            <p className="auth-switch">
              <Link to={ROUTES.DASHBOARD}>Return to dashboard</Link>
            </p>
          </>
        ) : (
          <div className="page-loading">
            <p>{accepting ? "Accepting invitation..." : "Preparing..."}</p>
          </div>
        )}
      </div>
    </AuthLayout>
  );
}

export default InvitationAcceptPage;
