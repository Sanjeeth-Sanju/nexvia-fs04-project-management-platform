
import { Navigate, Route, Routes, useSearchParams } from "react-router-dom";

import LandingPage from "../features/landing/LandingPage";
import LoginPage from "../features/auth/LoginPage";
import RegisterPage from "../features/auth/RegisterPage";
import DashboardPage from "../features/dashboard/DashboardPage";
import WorkspacePage from "../features/workspaces/WorkspacePage";
import ProjectsPage from "../features/projects/ProjectsPage";
import IssueDetailsPage from "../features/issues/IssueDetailsPage";
import MembersPage from "../features/members/MembersPage";
import InvitationAcceptPage from "../features/members/InvitationAcceptPage";
import ProjectDetailsPage from "../features/projects/ProjectDetailsPage";
import SettingsPage from "../features/settings/SettingsPage";
import ActivityPage from "../features/activity/ActivityPage";
import BillingPage from "../features/billing/BillingPage";

import ProtectedRoute from "../components/navigation/ProtectedRoute";
import AppLayout from "../components/layout/AppLayout";

import { ROUTES } from "../constants/routes";

function ComingSoon({ title }) {
  return (
    <main className="container">
      <h1>{title}</h1>
      <p>This page is under development.</p>
    </main>
  );
}

function BoardRouteRedirect() {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project");

  return (
    <Navigate
      to={projectId ? `/projects/${projectId}` : ROUTES.PROJECTS}
      replace
    />
  );
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path={ROUTES.HOME} element={<LandingPage />} />
      <Route path={ROUTES.LOGIN} element={<LoginPage />} />
      <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
      <Route path="/invitations/accept/:token" element={<InvitationAcceptPage />} />

      {/* Protected application routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path={ROUTES.DASHBOARD} element={<DashboardPage />} />

          <Route
            path={ROUTES.WORKSPACES}
            element={<WorkspacePage />}
          />

          <Route
            path={ROUTES.PROJECTS}
            element={<ProjectsPage />}
          />
          <Route path="/projects/:projectId" element={<ProjectDetailsPage />} />

          <Route
            path={ROUTES.MEMBERS}
            element={<MembersPage />}
          />

          <Route path={ROUTES.BOARD} element={<BoardRouteRedirect />} />
          <Route path="/issues/:issueId" element={<IssueDetailsPage />} />

          <Route path={ROUTES.SETTINGS} element={<SettingsPage />} />

          <Route
            path={ROUTES.BILLING}
            element={<BillingPage />}
          />

          <Route path={ROUTES.ACTIVITY} element={<ActivityPage />} />
        </Route>
      </Route>

      {/* Fallback */}
      <Route
        path="*"
        element={<Navigate to={ROUTES.HOME} replace />}
      />
    </Routes>
  );
}

export default AppRoutes;
