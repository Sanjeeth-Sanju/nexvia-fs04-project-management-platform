
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, ArrowRight } from "lucide-react";

import AuthLayout from "./components/AuthLayout";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import { ROUTES } from "../../constants/routes";

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [formData, setFormData] = useState({
    identifier: "",
    password: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));

    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!formData.identifier.trim() || !formData.password) {
      setError("Please enter your username/email and password.");
      return;
    }

    setLoading(true);

    try {
      await login({
        identifier: formData.identifier.trim(),
        password: formData.password,
      });

      const destination =
        location.state?.from?.pathname || ROUTES.DASHBOARD;

      navigate(destination, { replace: true });
    } catch (err) {
      setError(
        err.data?.detail ||
        err.message ||
        "Unable to log in. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue managing your team's work."
    >
      <form className="auth-form" onSubmit={handleSubmit}>
        {error && (
          <div className="auth-error" role="alert">
            {error}
          </div>
        )}

        <Input
          label="Email or username"
          name="identifier"
          placeholder="Enter your email or username"
          value={formData.identifier}
          onChange={handleChange}
          autoComplete="username"
          required
          disabled={loading}
        />

        <div className="auth-password-field">
          <Input
            label="Password"
            name="password"
            type={showPassword ? "text" : "password"}
            placeholder="Enter your password"
            value={formData.password}
            onChange={handleChange}
            autoComplete="current-password"
            required
            disabled={loading}
          />

          <button
            type="button"
            className="password-toggle"
            onClick={() => setShowPassword((previous) => !previous)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            disabled={loading}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        <Button
          type="submit"
          fullWidth
          size="large"
          loading={loading}
          disabled={loading}
        >
          Sign in
          {!loading && <ArrowRight size={17} />}
        </Button>

        <p className="auth-switch">
          Don't have an account?{" "}
          <Link to={ROUTES.REGISTER}>Create an account</Link>
        </p>
      </form>
    </AuthLayout>
  );
}

export default LoginPage;
