import { apiRequest } from "../../services/api";
export async function getWorkflowStatuses(id) {
  const data = await apiRequest(`/workspaces/${id}/workflow-statuses/`);
  return Array.isArray(data) ? data : data?.results || [];
}
export const createWorkflowStatus = (id, body) => apiRequest(`/workspaces/${id}/workflow-statuses/`, {method:"POST", body:JSON.stringify(body)});
export const updateWorkflowStatus = (id, sid, body) => apiRequest(`/workspaces/${id}/workflow-statuses/${sid}/`, {method:"PATCH", body:JSON.stringify(body)});
export const deleteWorkflowStatus = (id, sid) => apiRequest(`/workspaces/${id}/workflow-statuses/${sid}/`, {method:"DELETE"});
export const reorderWorkflowStatuses = (id, ids) => apiRequest(`/workspaces/${id}/workflow-statuses/reorder/`, {method:"POST", body:JSON.stringify({status_ids:ids})});

export async function updateProfile(formData) {
  return apiRequest("/auth/profile/", {
    method: "PATCH",
    body: formData,
  });
}

export const requestPasswordChange = () =>
  apiRequest("/auth/password-change/request/", {
    method: "POST",
    body: JSON.stringify({}),
  });

export const verifyPasswordChange = (otp) =>
  apiRequest("/auth/password-change/verify/", {
    method: "POST",
    body: JSON.stringify({ otp }),
  });

export const confirmPasswordChange = (payload) =>
  apiRequest("/auth/password-change/confirm/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// Workspace data export
export const requestWorkspaceDataExport = (workspaceIds) =>
  apiRequest("/auth/data-export/", {
    method: "POST",
    body: JSON.stringify({ workspace_ids: workspaceIds }),
  });

// Account deletion
export const getAccountDeletionImpact = () =>
  apiRequest("/auth/account-deletion/impact/");

export const confirmAccountDeletion = (payload) =>
  apiRequest("/auth/account-deletion/confirm/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
