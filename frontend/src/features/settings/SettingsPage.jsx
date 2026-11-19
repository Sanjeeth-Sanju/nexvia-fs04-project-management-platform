import { useToast } from "../../context/ToastContext";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, LockKeyhole, UserRound } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { updateProfile } from "./settingsService";
import PasswordSecuritySection from "./PasswordSecuritySection";
import AccountActionsSections from "./AccountActionsSections";

function getInitials(name, email) {
  const source = name?.trim() || email?.trim() || "U";
  return source
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

function formatDate(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

export default function SettingsPage() {
  const { user, updateUser } = useAuth();
const [activeSection, setActiveSection] = useState(null);
  const toast = useToast();

  function toggleSettingsSection(section) {
    const next = activeSection === section ? null : section;
    setActiveSection(next);

    const hashes = {
      profile: "#profile",
      password: "#security",
      export: "#data-export",
      delete: "#delete-account",
    };

    window.history.replaceState(
      null,
      "",
      next ? hashes[next] : window.location.pathname
    );
  }

  const fileInputRef = useRef(null);

  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [avatarFile, setAvatarFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [removingAvatar, setRemovingAvatar] = useState(false);
  useEffect(() => {
    setDisplayName(user?.display_name || "");
  }, [user?.display_name]);

  useEffect(() => {
    if (!avatarFile) {
      setPreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(avatarFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [avatarFile]);

  const avatarUrl = previewUrl || user?.avatar_url || null;
  const hasUnsavedChanges =
    displayName.trim() !== (user?.display_name || "").trim() ||
    Boolean(avatarFile);

  const initials = getInitials(displayName, user?.email);

  function handleAvatarChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    
    

    if (!file.type.startsWith("image/")) {
      toast.error("Choose a valid image file.");
      event.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error("Your profile image must be 5 MB or smaller.");
      event.target.value = "";
      return;
    }

    setAvatarFile(file);
  }

  async function handleSave(event) {
    event.preventDefault();
    
    

    const cleanedName = displayName.trim();
    if (!cleanedName) {
      toast.error("Display name cannot be empty.");
      return;
    }

    if (cleanedName.length > 120) {
      toast.error("Display name must be 120 characters or fewer.");
      return;
    }

    const formData = new FormData();
    formData.append("display_name", cleanedName);
    if (avatarFile) formData.append("avatar", avatarFile);

    setSaving(true);
    try {
      const result = await updateProfile(formData);
      updateUser({
        display_name: result.display_name,
        avatar_url: result.avatar_url,
      });
      setAvatarFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      toast.success("Your profile has been updated.");
    } catch (err) {
      toast.error(err.message || "Unable to update your profile.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemoveAvatar() {
    if (!user?.avatar_url && !avatarFile) return;

    
    

    if (avatarFile && !user?.avatar_url) {
      setAvatarFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    const formData = new FormData();
    formData.append("remove_avatar", "true");

    setRemovingAvatar(true);
    try {
      const result = await updateProfile(formData);
      updateUser({
        display_name: result.display_name,
        avatar_url: result.avatar_url,
      });
      setAvatarFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      toast.success("Your profile photo has been removed.");
    } catch (err) {
      toast.error(err.message || "Unable to remove your profile photo.");
    } finally {
      setRemovingAvatar(false);
    }
  }

  return (
    <main className="container phase2-page">
      <header className="phase2-page-header">
        <div>
          <p className="phase2-eyebrow">ACCOUNT PREFERENCES</p>
          <h1>Settings</h1>
          <p className="phase2-description">
            Manage your account details and personal preferences.
          </p>
        </div>
      </header>

        <section className="settings-account-card" aria-label="Account settings">
          <p className="settings-account-label">ACCOUNT</p>

          <button
            type="button"
            className={`settings-accordion-trigger ${activeSection === "profile" ? "is-open" : ""}`}
            aria-expanded={activeSection === "profile"}
            aria-controls="settings-profile-panel"
            onClick={() => toggleSettingsSection("profile")}
          >
            <UserRound size={19} strokeWidth={1.9} />
            <span>Profile</span>
            <span className="settings-accordion-chevron">
              {activeSection === "profile"
                ? <ChevronDown size={19} />
                : <ChevronRight size={19} />}
            </span>
          </button>

          <div
            id="settings-profile-panel"
            className={`settings-accordion-panel ${activeSection === "profile" ? "is-open" : ""}`}
            aria-hidden={activeSection !== "profile"}
            inert={activeSection !== "profile"}
          >
            <div className="settings-accordion-panel-inner">
              <section
                        className="settings-content"
                        id="profile"
                        aria-labelledby="profile-heading"
                      >
                        <div className="settings-section-heading">
                          <span className="settings-section-icon" aria-hidden="true"><UserRound size={21} strokeWidth={1.9} /></span>
                          <div>
                            <h2 id="profile-heading">Profile information</h2>
                            <p>Update how your identity appears across Nexvia.</p>
                          </div>
                        </div>

                        <form className="profile-settings-form" onSubmit={handleSave}>
                          <div className="profile-avatar-panel">
                            <div className="profile-avatar" aria-label="Profile photo preview">
                              {avatarUrl ? (
                                <img src={avatarUrl} alt="Your profile" />
                              ) : (
                                <span>{initials}</span>
                              )}
                            </div>

                            <div className="profile-avatar-copy">
                              <strong>Profile photo</strong>
                              <p>Use a clear image so your teammates can recognise you.</p>
                              <div className="profile-avatar-actions">
                                <button
                                  type="button"
                                  className="phase2-button phase2-button--secondary"
                                  onClick={() => fileInputRef.current?.click()}
                                >
                                  Choose image
                                </button>
                                {(user?.avatar_url || avatarFile) && (
                                  <button
                                    type="button"
                                    className="profile-remove-button"
                                    onClick={handleRemoveAvatar}
                                    disabled={removingAvatar || saving}
                                  >
                                    {removingAvatar ? "Removing..." : "Remove photo"}
                                  </button>
                                )}
                              </div>
                              <small>JPG, PNG, GIF or WebP · Maximum 5 MB</small>
                              <input
                                ref={fileInputRef}
                                className="profile-file-input"
                                type="file"
                                accept="image/*"
                                onChange={handleAvatarChange}
                                aria-label="Choose profile photo"
                              />
                            </div>
                          </div>

                          <div className="profile-form-divider" />

                          <label className="phase2-field">
                            Display name
                            <input
                              type="text"
                              value={displayName}
                              onChange={(event) => setDisplayName(event.target.value)}
                              maxLength={120}
                              autoComplete="name"
                              placeholder="Your display name"
                              required
                            />
                            <small>This name is visible to members in your workspaces.</small>
                          </label>

                          <label className="phase2-field">
                            Email address
                            <input
                              type="email"
                              value={user?.email || ""}
                              disabled
                              readOnly
                            />
                            <small>
                              Your account identifier. Email changes are not available here.
                            </small>
                          </label>

                          <div className="profile-account-details">
                            <div>
                              <span>Account created</span>
                              <strong>{formatDate(user?.date_joined)}</strong>
                            </div>
                            <div>
                              <span>Account status</span>
                              <strong className={user?.is_active ? "profile-active" : "profile-inactive"}>
                                <span aria-hidden="true">●</span>
                                {user?.is_active ? "Active" : "Inactive"}
                              </strong>
                            </div>
                          </div>

                          <div className="profile-save-row">
                            <button
                              type="submit"
                              className="phase2-button phase2-button--primary"
                              disabled={saving || removingAvatar || !hasUnsavedChanges}
                            >
                              {saving ? "Saving changes..." : "Save changes"}
                            </button>
                          </div>
                        </form>
                      </section>
            </div>
          </div>

          <div className="settings-account-divider" />

          <button
            type="button"
            className={`settings-accordion-trigger ${activeSection === "password" ? "is-open" : ""}`}
            aria-expanded={activeSection === "password"}
            aria-controls="settings-password-panel"
            onClick={() => toggleSettingsSection("password")}
          >
            <LockKeyhole size={19} strokeWidth={1.9} />
            <span>Change Password</span>
            <span className="settings-accordion-chevron">
              {activeSection === "password"
                ? <ChevronDown size={19} />
                : <ChevronRight size={19} />}
            </span>
          </button>

          <div
            id="settings-password-panel"
            className={`settings-accordion-panel ${activeSection === "password" ? "is-open" : ""}`}
            aria-hidden={activeSection !== "password"}
            inert={activeSection !== "password"}
          >
            <div className="settings-accordion-panel-inner">
              <PasswordSecuritySection />
            </div>
          </div>

          <AccountActionsSections activeSection={activeSection} onToggle={toggleSettingsSection} />
        </section>
      </main>
    );
  }
