import { apiRequest } from "../../services/api";

export function createWorkspace(name) {
  return apiRequest("/workspaces/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function deleteWorkspace(workspaceId) {
  return apiRequest(`/workspaces/${workspaceId}/`, {
    method: "DELETE",
  });
}

export function updateWorkspace(workspaceId, body) {
  return apiRequest(`/workspaces/${workspaceId}/`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}
