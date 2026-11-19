import { useCallback, useEffect, useRef, useState } from "react";
import {
  Users,
  UserPlus,
  Mail,
  Shield,
  Clock,
  RefreshCw,
  X,
  Check,
  ChevronDown,
  FolderKanban,
  SquarePen,
} from "lucide-react";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useToast } from "../../context/ToastContext";
import {
  getWorkspaceMembers,
  getInvitations,
  inviteMember,
  revokeInvitation,
  updateMemberProjectAssignments,
  updateWorkspaceMemberRole,
  removeWorkspaceMember,
} from "./memberService";
import { getProjects } from "../projects/projectService";
import Modal from "../../components/ui/Modal";

export default function MembersPage() {
  const { selectedWorkspace } = useWorkspace();
  const { success, error } = useToast();

  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [roleOpen, setRoleOpen] = useState(false);
  const [projects, setProjects] = useState([]);
  const [selectedProjectIds, setSelectedProjectIds] = useState([]);
  const [projectPickerOpen, setProjectPickerOpen] = useState(false);
  const projectPickerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [revokingId, setRevokingId] = useState(null);
  const [editingMemberId, setEditingMemberId] = useState(null);
  const [editProjectIds, setEditProjectIds] = useState([]);
  const [editProjectPickerOpen, setEditProjectPickerOpen] = useState(false);
  const [savingAssignmentId, setSavingAssignmentId] = useState(null);
  const editProjectPickerRef = useRef(null);
  const editingMember = members.find(
    (member) => String(member.user_id) === String(editingMemberId)
  );

  const workspaceId = selectedWorkspace?.id;
  const currentRole = selectedWorkspace?.current_user_role;
  const canManage = ["owner", "admin"].includes(currentRole);
  const isOwner = currentRole === "owner";
  const [editMemberRole, setEditMemberRole] = useState("member");
  const [editMemberRoleOpen, setEditMemberRoleOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState(null);
  const [removingMemberId, setRemovingMemberId] = useState(null);

  const loadData = useCallback(async () => {
    if (!workspaceId) {
      setMembers([]);
      setInvitations([]);
      setLoading(false);
      return;
    }

    setLoading(true);

    try {
      const memberData = await getWorkspaceMembers(workspaceId);
      setMembers(Array.isArray(memberData) ? memberData : memberData.results || []);

      if (canManage) {
        const projectData = await getProjects();
        const availableProjects = Array.isArray(projectData)
          ? projectData
          : projectData.results || [];
        const workspaceProjects = availableProjects.filter(
          (project) => String(project.workspace) === String(workspaceId)
        );
        setProjects(workspaceProjects);
        setSelectedProjectIds((current) =>
          current.filter((id) =>
            workspaceProjects.some((project) => String(project.id) === String(id))
          )
        );
      } else {
        setProjects([]);
        setSelectedProjectIds([]);
      }

      if (canManage) {
        const invitationData = await getInvitations(workspaceId);
        setInvitations(
          Array.isArray(invitationData)
            ? invitationData
            : invitationData.results || []
        );
      } else {
        setInvitations([]);
      }
    } catch (err) {
      error(err.message || "Unable to load workspace members.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, canManage, error]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!projectPickerOpen) return;

    function handleOutsidePointer(event) {
      if (!projectPickerRef.current?.contains(event.target)) {
        setProjectPickerOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setProjectPickerOpen(false);
      }
    }

    document.addEventListener("pointerdown", handleOutsidePointer);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("pointerdown", handleOutsidePointer);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [projectPickerOpen]);


  async function handleInvite(event) {
    event.preventDefault();

    if (!email.trim()) return;

    if (role === "member" && selectedProjectIds.length === 0) {
      error("Select at least one project for this member.");
      return;
    }

    setSubmitting(true);

    try {
      const result = await inviteMember(workspaceId, {
        email: email.trim(),
        role,
        ...(role === "member" ? { project_ids: selectedProjectIds } : {}),
      });

      setEmail("");
      setSelectedProjectIds([]);
      setProjectPickerOpen(false);
      success(
        result.email_sent === false
          ? "Invitation created, but the email could not be sent."
          : "Invitation sent successfully."
      );
      await loadData();
    } catch (err) {
      error(err.message || "Unable to send invitation.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRevoke(invitationId) {
    setRevokingId(invitationId);

    try {
      await revokeInvitation(invitationId);
      success("Invitation revoked.");
      await loadData();
    } catch (err) {
      error(err.message || "Unable to revoke invitation.");
    } finally {
      setRevokingId(null);
    }
  }

  function startEditingAssignments(member) {
    setEditingMemberId(member.user_id);
    setEditMemberRole(member.role);
    setEditMemberRoleOpen(false);
    setEditProjectIds((member.project_ids || []).map(Number));
    setEditProjectPickerOpen(false);
  }

  async function saveMemberAssignments(member) {
    const userId = member.user_id;
    setSavingAssignmentId(userId);

    try {
      let result;

      if (isOwner) {
        result = await updateWorkspaceMemberRole(
          workspaceId,
          userId,
          editMemberRole,
          editMemberRole === "member" ? editProjectIds : []
        );
      } else {
        result = await updateMemberProjectAssignments(
          workspaceId,
          userId,
          editProjectIds
        );
      }

      const updatedIds = (result.project_ids || (
        editMemberRole === "member" ? editProjectIds : []
      )).map(Number);

      const updatedProjects = projects
        .filter((project) => updatedIds.includes(Number(project.id)))
        .map((project) => ({
          id: project.id,
          name: project.name,
          key: project.key,
        }));

      setMembers((current) =>
        current.map((item) =>
          String(item.user_id) === String(userId)
            ? {
                ...item,
                role: isOwner ? editMemberRole : item.role,
                project_ids: updatedIds,
                projects: updatedProjects,
              }
            : item
        )
      );

      setEditingMemberId(null);
      setEditProjectPickerOpen(false);
      setEditMemberRoleOpen(false);

      if (result.email_sent === false) {
        success("Member access updated, but the notification email could not be sent.");
      } else {
        success(
          isOwner && result.email_sent === true
            ? "Member access updated and notification email sent."
            : "Member details updated."
        );
      }
    } catch (err) {
      error(err.message || "Unable to update member details.");
      await loadData();
    } finally {
      setSavingAssignmentId(null);
    }
  }

  async function confirmRemoveMember() {
    if (!removeTarget) return;

    const userId = removeTarget.user_id;
    setRemovingMemberId(userId);

    try {
      await removeWorkspaceMember(workspaceId, userId);
      setMembers((current) =>
        current.filter((item) => String(item.user_id) !== String(userId))
      );
      setRemoveTarget(null);
      success("Member removed from workspace.");
    } catch (err) {
      error(err.message || "Unable to remove workspace member.");
    } finally {
      setRemovingMemberId(null);
    }
  }

  if (!selectedWorkspace) {
    return <div className="page-container"><h2>Select a workspace</h2></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Members</h1>
          <p>Manage the people working in {selectedWorkspace.name}.</p>
        </div>
        <button className="btn btn-secondary" onClick={loadData} disabled={loading}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {canManage && (
        <section className="card members-invite-card">
          <div className="members-invite-heading">
            <div className="members-heading-icon">
              <UserPlus size={19} />
            </div>
            <h2>Invite a member</h2>
          </div>

          <form className="members-invite-form" onSubmit={handleInvite}>
            <label>
              Email address
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@example.com"
                required
              />
            </label>

            <div className="members-role-field">
              <label>Workspace role</label>
              <div className="members-role-dropdown">
                <button
                  type="button"
                  className={`members-role-trigger ${roleOpen ? "is-open" : ""}`}
                  onClick={() => setRoleOpen((open) => !open)}
                  aria-expanded={roleOpen}
                  aria-haspopup="listbox"
                >
                  <span>{role === "admin" ? "Admin" : "Member"}</span>
                  <ChevronDown size={17} />
                </button>

                {roleOpen && (
                  <div className="members-role-menu" role="listbox" aria-label="Workspace role">
                    {[
                      { value: "member", label: "Member" },
                      { value: "admin", label: "Admin" },
                    ].map((option) => (
                      <button
                        type="button"
                        role="option"
                        aria-selected={role === option.value}
                        key={option.value}
                        className={`members-role-option ${role === option.value ? "selected" : ""}`}
                        onClick={() => {
                          setRole(option.value);
                          setRoleOpen(false);
                          if (option.value === "admin") {
                            setSelectedProjectIds([]);
                            setProjectPickerOpen(false);
                          }
                        }}
                      >
                        <span>{option.label}</span>
                        {role === option.value && <Check size={16} />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {role === "member" && (
              <div className="members-project-field">
                <label>Assign projects to this member</label>
                <div className="members-project-picker" ref={projectPickerRef}>
                  <button
                    type="button"
                    className={`members-project-trigger ${projectPickerOpen ? "is-open" : ""}`}
                    onClick={() => setProjectPickerOpen((open) => !open)}
                    aria-expanded={projectPickerOpen}
                    aria-haspopup="listbox"
                    disabled={projects.length === 0}
                  >
                    <span>
                      <FolderKanban size={16} />
                      {selectedProjectIds.length
                        ? `${selectedProjectIds.length} project${selectedProjectIds.length === 1 ? "" : "s"} selected`
                        : "Choose projects"}
                    </span>
                    <ChevronDown size={17} />
                  </button>

                  {projectPickerOpen && (
                    <div className="members-project-menu" role="listbox" aria-multiselectable="true">
                      {projects.map((project) => {
                        const selected = selectedProjectIds.some(
                          (id) => String(id) === String(project.id)
                        );

                        return (
                          <button
                            type="button"
                            key={project.id}
                            role="option"
                            aria-selected={selected}
                            className={`members-project-option ${selected ? "selected" : ""}`}
                            onClick={() =>
                              setSelectedProjectIds((current) =>
                                selected
                                  ? current.filter((id) => String(id) !== String(project.id))
                                  : [...current, project.id]
                              )
                            }
                          >
                            <span className="members-project-checkbox">
                              {selected && <Check size={13} />}
                            </span>
                            <span className="members-project-option-details">
                              <strong>{project.name}</strong>
                              <small>{project.key}</small>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                <p className="members-project-help">
                  {projects.length === 0
                    ? "Create a project before inviting a member."
                    : "Members can access only the projects selected here. You can change access later."}
                </p>
              </div>
            )}

            <button
              className="btn btn-primary"
              type="submit"
              disabled={
                submitting ||
                !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) ||
                (role === "member" &&
                  (projects.length === 0 || selectedProjectIds.length === 0))
              }
            >
              <Mail size={16} />
              {submitting ? "Sending..." : "Send invitation"}
            </button>
          </form>
        </section>
      )}

      <section className="members-section">
        <div className="members-section-heading">
          <div>
            <h2><Users size={19} /> Workspace members</h2>
            <p>{members.length} {members.length === 1 ? "person" : "people"} in this workspace</p>
          </div>
        </div>

        {loading ? (
          <div className="members-empty">Loading members...</div>
        ) : members.length === 0 ? (
          <div className="members-empty">No members found.</div>
        ) : (
          <div className="members-list">
            {members.map((member) => {
              const displayName =
                [member.first_name, member.last_name].filter(Boolean).join(" ") ||
                member.username ||
                member.email;

              const assignedProjects = member.projects || [];

              return (
                <div key={member.id}>
                  <div className="member-row">
                    <div className="member-avatar">
                      {displayName?.charAt(0)?.toUpperCase() || "U"}
                    </div>
                    <div className="member-details">
                      <strong>{displayName}</strong>
                      <span>{member.email}</span>
                      {member.role === "member" && (
                        <span>
                          {assignedProjects.length
                            ? `Projects: ${assignedProjects.map((project) => project.name).join(", ")}`
                            : "No projects assigned"}
                        </span>
                      )}
                    </div>
                    <span className={`member-role role-${member.role}`}>
                      <Shield size={13} />
                      {member.role}
                    </span>
                    {canManage && member.role !== "owner" && (
                      <>
                        <button
                          type="button"
                          className="members-manage-access"
                          onClick={() => startEditingAssignments(member)}
                          aria-label={`Edit ${member.email}`}
                          title="Edit member"
                        >
                          <SquarePen size={17} strokeWidth={1.8} />
                        </button>
                        {isOwner && (
                          <button
                            type="button"
                            className="members-remove-member"
                            onClick={() => setRemoveTarget(member)}
                            aria-label={`Remove ${member.email} from workspace`}
                            title="Remove from workspace"
                          >
                            <X size={17} />
                          </button>
                        )}
                      </>
                    )}
                  </div>


                </div>
              );
            })}
          </div>
        )}
      </section>

      {canManage && (
        <section className="members-section">
          <div className="members-section-heading">
            <div>
              <h2><Clock size={19} /> Pending invitations</h2>
              <p>Invitations that are awaiting acceptance.</p>
            </div>
          </div>

          {invitations.filter((item) => item.status === "pending").length === 0 ? (
            <div className="members-empty">No pending invitations.</div>
          ) : (
            <div className="members-list">
              {invitations
                .filter((item) => item.status === "pending")
                .map((invitation) => (
                  <div className="member-row" key={invitation.id}>
                    <div className="member-avatar invitation-avatar">
                      <Mail size={17} />
                    </div>
                    <div className="member-details">
                      <strong>{invitation.email}</strong>
                      <span>
                        Expires {new Date(invitation.expires_at).toLocaleDateString()}
                      </span>
                    </div>
                    <span className={`member-role role-${invitation.role}`}>
                      {invitation.role}
                    </span>
                    <button
                      className="member-revoke-button"
                      onClick={() => handleRevoke(invitation.id)}
                      disabled={revokingId === invitation.id}
                      title="Revoke invitation"
                      aria-label={`Revoke invitation for ${invitation.email}`}
                    >
                      <X size={17} />
                    </button>
                  </div>
                ))}
            </div>
          )}
        </section>
      )}

      <Modal
        open={Boolean(canManage && editingMember)}
        onClose={() => {
          if (savingAssignmentId === null) {
            setEditingMemberId(null);
            setEditProjectPickerOpen(false);
          }
        }}
        titleId="member-access-modal-title"
        size="medium"
      >
        {editingMember && (
          <div className="members-assignment-modal">
            <div className="members-assignment-modal-heading">
              <span className="members-assignment-modal-icon">
                <FolderKanban size={20} />
              </span>
              <div>
                <h2 id="member-access-modal-title">Manage project access</h2>
                <p>{[editingMember.first_name, editingMember.last_name].filter(Boolean).join(" ") || editingMember.username || editingMember.email}</p>
                <span>{editingMember.email}</span>
              </div>
            </div>

            <div className="members-assignment-modal-body">
              {isOwner && editingMember.role !== "owner" && (
                <div className="members-edit-role-field">
                  <label className="members-assignment-modal-label">Workspace role</label>
                  <div className="members-edit-role-dropdown">
                    <button
                      type="button"
                      className={`members-role-trigger ${editMemberRoleOpen ? "is-open" : ""}`}
                      onClick={() => setEditMemberRoleOpen((open) => !open)}
                      aria-expanded={editMemberRoleOpen}
                      aria-haspopup="listbox"
                    >
                      <span>{editMemberRole === "admin" ? "Admin" : "Member"}</span>
                      <ChevronDown size={17} />
                    </button>
                    {editMemberRoleOpen && (
                      <div className="members-role-menu" role="listbox" aria-label="Workspace role">
                        {[
                          { value: "member", label: "Member" },
                          { value: "admin", label: "Admin" },
                        ].map((option) => (
                          <button
                            key={option.value}
                            type="button"
                            role="option"
                            aria-selected={editMemberRole === option.value}
                            className={`members-role-option ${editMemberRole === option.value ? "selected" : ""}`}
                            onClick={() => {
                              setEditMemberRole(option.value);
                              setEditMemberRoleOpen(false);
                            }}
                          >
                            <span>{option.label}</span>
                            {editMemberRole === option.value && <Check size={15} />}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {editMemberRole === "member" && (
                <>
              <label className="members-assignment-modal-label">
                Projects this member can access
              </label>

              <div className="members-project-picker" ref={editProjectPickerRef}>
                <button
                  type="button"
                  className={`members-project-trigger ${editProjectPickerOpen ? "is-open" : ""}`}
                  onClick={() => setEditProjectPickerOpen((open) => !open)}
                  aria-expanded={editProjectPickerOpen}
                  aria-haspopup="listbox"
                  disabled={projects.length === 0}
                >
                  <span>
                    <FolderKanban size={16} />
                    {editProjectIds.length
                      ? `${editProjectIds.length} project${editProjectIds.length === 1 ? "" : "s"} selected`
                      : "Choose projects"}
                  </span>
                  <ChevronDown size={17} />
                </button>

                {editProjectPickerOpen && (
                  <div
                    className="members-project-menu"
                    role="listbox"
                    aria-multiselectable="true"
                  >
                    {projects.map((project) => {
                      const selected = editProjectIds.some(
                        (id) => Number(id) === Number(project.id)
                      );

                      return (
                        <button
                          type="button"
                          key={project.id}
                          role="option"
                          aria-selected={selected}
                          className={`members-project-option ${selected ? "selected" : ""}`}
                          onClick={() =>
                            setEditProjectIds((current) =>
                              selected
                                ? current.filter((id) => Number(id) !== Number(project.id))
                                : [...current, Number(project.id)]
                            )
                          }
                        >
                          <span className="members-project-checkbox">
                            {selected && <Check size={13} />}
                          </span>
                          <span className="members-project-option-details">
                            <strong>{project.name}</strong>
                            <small>{project.key}</small>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="members-assignment-selection">
                {editProjectIds.length
                  ? `${editProjectIds.length} of ${projects.length} projects selected`
                  : "No projects selected"}
              </div>

              <p className="members-project-help">
                Removing project access does not delete this member's existing issues, comments or activity.
              </p>
                </>
              )}
            </div>

            <div className="members-assignment-modal-actions">
              <button
                type="button"
                className="members-assignment-cancel"
                disabled={savingAssignmentId !== null}
                onClick={() => {
                  setEditingMemberId(null);
                  setEditProjectPickerOpen(false);
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="members-assignment-confirm"
                disabled={savingAssignmentId !== null || projects.length === 0}
                onClick={() => saveMemberAssignments(editingMember)}
              >
                {savingAssignmentId !== null ? "Saving..." : "Save changes"}
              </button>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        open={Boolean(removeTarget)}
        onClose={() => {
          if (removingMemberId === null) setRemoveTarget(null);
        }}
        titleId="remove-member-modal-title"
        size="small"
      >
        {removeTarget && (
          <div className="members-remove-modal">
            <h2 id="remove-member-modal-title">Remove workspace member?</h2>
            <p>
              Remove <strong>{[removeTarget.first_name, removeTarget.last_name].filter(Boolean).join(" ") || removeTarget.username || removeTarget.email}</strong> from this workspace?
            </p>
            <p>
              Their account, projects, issues, comments, attachments and activity history will remain.
              Only workspace membership and project assignments will be removed.
            </p>
            <div className="members-remove-modal-actions">
              <button
                type="button"
                className="members-remove-cancel"
                disabled={removingMemberId !== null}
                onClick={() => setRemoveTarget(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="members-remove-confirm"
                disabled={removingMemberId !== null}
                onClick={confirmRemoveMember}
              >
                {removingMemberId !== null ? "Removing..." : "Remove member"}
              </button>
            </div>
          </div>
        )}
      </Modal>

    </div>
  );
}
