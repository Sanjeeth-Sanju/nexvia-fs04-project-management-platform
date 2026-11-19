
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, ArrowRight } from "lucide-react";

import AuthLayout from "./components/AuthLayout";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import { ROUTES } from "../../constants/routes";

function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    password_confirm: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;
    setFormData((previous) => ({ ...previous, [name]: value }));
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (formData.password !== formData.password_confirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await register({
        username: formData.username.trim(),
        email: formData.email.trim(),
        password: formData.password,
        password_confirm: formData.password_confirm,
      });

      navigate(ROUTES.LOGIN, {
        replace: true,
        state: { registered: true, from: location.state?.from },
      });
    } catch (err) {
      const details = err.data;
      const message =
        typeof details === "object" && details !== null
          ? details.detail ||
            Object.values(details).flat().join(" ") ||
            err.message
          : err.message;

      setError(message || "Unable to create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Bring your team's projects and collaboration into one place."
    >
      <form className="auth-form" onSubmit={handleSubmit}>
        {error && (
          <div className="auth-error" role="alert">
            {error}
          </div>
        )}

        <Input
          label="Username"
          name="username"
          placeholder="Choose a username"
          value={formData.username}
          onChange={handleChange}
          autoComplete="username"
          required
          disabled={loading}
        />

        <Input
          label="Email address"
          name="email"
          type="email"
          placeholder="you@example.com"
          value={formData.email}
          onChange={handleChange}
          autoComplete="email"
          required
          disabled={loading}
        />

        <div className="auth-password-field">
          <Input
            label="Password"
            name="password"
            type={showPassword ? "text" : "password"}
            placeholder="Create a password"
            value={formData.password}
            onChange={handleChange}
            autoComplete="new-password"
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

        <div className="auth-password-field">
          <Input
            label="Confirm password"
            name="password_confirm"
            type={showConfirmPassword ? "text" : "password"}
            placeholder="Enter your password again"
            value={formData.password_confirm}
            onChange={handleChange}
            autoComplete="new-password"
            required
            disabled={loading}
          />
          <button
            type="button"
            className="password-toggle"
            onClick={() =>
              setShowConfirmPassword((previous) => !previous)
            }
            aria-label={
              showConfirmPassword ? "Hide password" : "Show password"
            }
            disabled={loading}
          >
            {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        <Button
          type="submit"
          fullWidth
          size="large"
          loading={loading}
          disabled={loading}
        >
          Create account
          {!loading && <ArrowRight size={17} />}
        </Button>

        <p className="auth-switch">
          Already have an account?{" "}
          <Link to={ROUTES.LOGIN} state={{ from: location.state?.from }}>Sign in</Link>
        </p>
      </form>
    </AuthLayout>
  );
}

export default RegisterPage;
