import { apiRequest } from "../../services/api";

export function getBoards() {
  return apiRequest("/boards/");
}

export function createBoard(data) {
  return apiRequest("/boards/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getWorkflowStatuses(workspaceId) {
  return apiRequest(`/workspaces/${workspaceId}/workflow-statuses/`);
}
