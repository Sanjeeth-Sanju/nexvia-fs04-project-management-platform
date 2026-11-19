import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  KeyRound,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { ROUTES } from "../../constants/routes";
import {
  requestPasswordChange,
  verifyPasswordChange,
  confirmPasswordChange,
} from "./settingsService";

export default function PasswordSecuritySection() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState("request");
  const [emailHint, setEmailHint] = useState("");
  const [otp, setOtp] = useState("");
  const [authorization, setAuthorization] = useState("");
  const [resendSeconds, setResendSeconds] = useState(0);
  const [expiresIn, setExpiresIn] = useState(0);
  const [newPassword, setNewPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (resendSeconds <= 0) return undefined;
    const timer = window.setInterval(() => {
      setResendSeconds((current) => Math.max(0, current - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendSeconds > 0]);

  useEffect(() => {
    if (expiresIn <= 0 || step !== "verify") return undefined;
    const timer = window.setInterval(() => {
      setExpiresIn((current) => Math.max(0, current - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [step, expiresIn > 0]);

  function clearFeedback() {
    setError("");
    setMessage("");
  }

  async function handleRequestCode() {
    clearFeedback();
    setBusy(true);
    try {
      const result = await requestPasswordChange();
      setEmailHint(result.email_hint || user?.email || "");
      setResendSeconds(result.resend_after || 60);
      setExpiresIn(result.expires_in || 600);
      setOtp("");
      setAuthorization("");
      setStep("verify");
      setMessage(result.message || "Verification code sent.");
    } catch (err) {
      setError(err.message || "Unable to send the verification code.");
      if (err.data?.retry_after) {
        setResendSeconds(err.data.retry_after);
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(event) {
    event.preventDefault();
    clearFeedback();

    if (!/^\d{6}$/.test(otp)) {
      setError("Enter the six-digit code from your email.");
      return;
    }

    setBusy(true);
    try {
      const result = await verifyPasswordChange(otp);
      setAuthorization(result.authorization);
      setStep("password");
      setMessage("");
    } catch (err) {
      setError(err.message || "Unable to verify the code.");
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirm(event) {
    event.preventDefault();
    clearFeedback();

    if (newPassword.length < 1 || passwordConfirm.length < 1) {
      setError("Enter and confirm your new password.");
      return;
    }

    setBusy(true);
    try {
      await confirmPasswordChange({
        authorization,
        new_password: newPassword,
        password_confirm: passwordConfirm,
      });

      setStep("complete");
      setMessage("Your password has been changed. Please log in again.");

      // The backend has revoked all refresh tokens. Clear local auth state
      // even if the logout endpoint rejects the already-revoked cookie.
      try {
        await logout();
      } catch {
        // AuthContext.logout clears the local user in its finally block.
      }

      navigate(ROUTES.LOGIN, { replace: true });
    } catch (err) {
      setError(err.message || "Unable to change your password.");
    } finally {
      setBusy(false);
    }
  }

  function backToRequest() {
    clearFeedback();
    setStep("request");
    setOtp("");
    setAuthorization("");
    setNewPassword("");
    setPasswordConfirm("");
    setExpiresIn(0);
  }

  return (
    <section
      className="settings-content security-settings"
      id="security"
      aria-labelledby="security-heading"
    >
      <div className="settings-section-heading">
        <span className="settings-section-icon" aria-hidden="true">
          <ShieldCheck size={21} strokeWidth={1.9} />
        </span>
        <div>
          <h2 id="security-heading">Password & security</h2>
          <p>Protect your account by keeping your password up to date.</p>
        </div>
      </div>

      <div className="settings-info">
        <LockKeyhole size={18} />
        <p>
          Password changes require verification through your registered email.
          Verification codes expire after 10 minutes and can only be used once.
        </p>
      </div>

      {step === "request" && (
        <div className="security-step">
          <div className="security-account-email">
            <span className="security-email-icon"><Mail size={18} /></span>
            <div>
              <small>Verification email</small>
              <strong>{user?.email || "No email address available"}</strong>
            </div>
          </div>
          <p className="security-help">
            We will send a six-digit verification code to this address.
          </p>
          <button
            type="button"
            className="phase2-button phase2-button--primary"
            onClick={handleRequestCode}
            disabled={busy || !user?.email}
          >
            {busy ? "Sending code..." : "Send verification code"}
          </button>
        </div>
      )}

      {step === "verify" && (
        <form className="security-step" onSubmit={handleVerify}>
          <div className="security-step-heading">
            <KeyRound size={19} />
            <div>
              <strong>Verify your email</strong>
              <p>Enter the code sent to {emailHint || user?.email}.</p>
            </div>
          </div>

          <label className="phase2-field">
            Six-digit verification code
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={otp}
              onChange={(event) =>
                setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
              placeholder="000000"
              maxLength={6}
              required
            />
            <small>
              {expiresIn > 0
                ? `Code expires in ${Math.floor(expiresIn / 60)}:${String(expiresIn % 60).padStart(2, "0")}.`
                : "This code has expired. Request a new one."}
            </small>
          </label>

          <div className="security-actions">
            <button
              type="submit"
              className="phase2-button phase2-button--primary"
              disabled={busy || otp.length !== 6 || expiresIn <= 0}
            >
              {busy ? "Verifying..." : "Verify code"}
            </button>
            <button
              type="button"
              className="phase2-button phase2-button--secondary"
              onClick={handleRequestCode}
              disabled={busy || resendSeconds > 0}
            >
              {resendSeconds > 0
                ? `Resend in ${resendSeconds}s`
                : "Resend code"}
            </button>
          </div>
          <button
            type="button"
            className="security-text-button"
            onClick={backToRequest}
            disabled={busy}
          >
            Cancel password change
          </button>
        </form>
      )}

      {step === "password" && (
        <form className="security-step" onSubmit={handleConfirm}>
          <div className="security-step-heading">
            <ShieldCheck size={19} />
            <div>
              <strong>Email verified</strong>
              <p>Choose a strong new password for your account.</p>
            </div>
          </div>

          <label className="phase2-field">
            New password
            <input
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="Enter your new password"
              required
            />
          </label>

          <label className="phase2-field">
            Confirm new password
            <input
              type="password"
              autoComplete="new-password"
              value={passwordConfirm}
              onChange={(event) => setPasswordConfirm(event.target.value)}
              placeholder="Re-enter your new password"
              required
            />
          </label>

          <div className="security-actions">
            <button
              type="submit"
              className="phase2-button phase2-button--primary"
              disabled={busy || !newPassword || !passwordConfirm}
            >
              {busy ? "Changing password..." : "Change password"}
            </button>
            <button
              type="button"
              className="phase2-button phase2-button--secondary"
              onClick={backToRequest}
              disabled={busy}
            >
              Start over
            </button>
          </div>
        </form>
      )}

      {step === "complete" && (
        <div className="security-complete" role="status">
          <ShieldCheck size={23} />
          <div>
            <strong>Password changed successfully</strong>
            <p>You are being redirected to sign in with your new password.</p>
          </div>
        </div>
      )}

      {error && (
        <p className="profile-feedback profile-feedback--error" role="alert">
          {error}
        </p>
      )}
      {message && step !== "complete" && (
        <p className="profile-feedback profile-feedback--success" role="status">
          {message}
        </p>
      )}
    </section>
  );
}
