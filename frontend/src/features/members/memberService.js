import { apiRequest } from "../../services/api";

export function getWorkspaceMembers(workspaceId) {
  return apiRequest(`/workspaces/${workspaceId}/members/`);
}

export function getInvitations(workspaceId) {
  return apiRequest(`/workspaces/${workspaceId}/invitations/`);
}

export function inviteMember(workspaceId, data) {
  return apiRequest(`/workspaces/${workspaceId}/invitations/`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function revokeInvitation(invitationId) {
  return apiRequest(`/invitations/${invitationId}/revoke/`, {
    method: "POST",
  });
}


export function acceptInvitation(token) {
  return apiRequest(`/invitations/${token}/accept/`, {
    method: "POST",
  });
}

export function updateMemberProjectAssignments(workspaceId, userId, projectIds) {
  return apiRequest(`/workspaces/${workspaceId}/members/${userId}/projects/`, {
    method: "PUT",
    body: JSON.stringify({ project_ids: projectIds }),
  });
}


export function updateWorkspaceMemberRole(workspaceId, userId, role, projectIds = []) {
  return apiRequest(`/workspaces/${workspaceId}/members/${userId}/role/`, {
    method: "PATCH",
    body: JSON.stringify({ role, project_ids: projectIds }),
  });
}

export function removeWorkspaceMember(workspaceId, userId) {
  return apiRequest(`/workspaces/${workspaceId}/members/${userId}/`, {
    method: "DELETE",
  });
}
