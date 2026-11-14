
import { Navigate, Route, Routes } from "react-router-dom";

import LandingPage from "../features/landing/LandingPage";
import LoginPage from "../features/auth/LoginPage";
import RegisterPage from "../features/auth/RegisterPage";
import ProtectedRoute from "../components/navigation/ProtectedRoute";
import { ROUTES } from "../constants/routes";


function ComingSoon({ title }) {
  return (
    <main className="container">
      <h1>{title}</h1>
      <p>This page is under development.</p>
    </main>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path={ROUTES.HOME} element={<LandingPage />} />

      <Route path={ROUTES.LOGIN} element={<LoginPage />} />

      <Route path={ROUTES.REGISTER} element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route
          path={ROUTES.DASHBOARD}
          element={<ComingSoon title="Dashboard" />}
        />
        <Route
          path={ROUTES.WORKSPACES}
          element={<ComingSoon title="Workspaces" />}
        />
        <Route
          path={ROUTES.PROJECTS}
          element={<ComingSoon title="Projects" />}
        />
        <Route
          path={ROUTES.BOARD}
          element={<ComingSoon title="Board" />}
        />
        <Route
          path={ROUTES.SETTINGS}
          element={<ComingSoon title="Settings" />}
        />
        <Route
          path={ROUTES.BILLING}
          element={<ComingSoon title="Billing" />}
        />
        <Route
          path={ROUTES.ACTIVITY}
          element={<ComingSoon title="Activity" />}
        />
      </Route>

      <Route path="*" element={<Navigate to={ROUTES.HOME} replace />} />
    </Routes>
  );
}

export default AppRoutes;
