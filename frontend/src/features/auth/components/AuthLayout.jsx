
import { Link } from "react-router-dom";
import { ROUTES } from "../../../constants/routes";

function AuthLayout({ children, title, subtitle }) {
  return (
    <main className="auth-page">
      <div className="auth-brand">
        <Link to={ROUTES.HOME}>NEXVIA</Link>
        <span>PROJECT MANAGEMENT, REFINED.</span>
      </div>

      <section className="auth-card">
        <div className="auth-card-heading">
          <p className="auth-eyebrow">WELCOME TO NEXVIA</p>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>

        {children}
      </section>

      <footer className="auth-footer">
        Built for teams that move forward.
      </footer>
    </main>
  );
}

export default AuthLayout;
