import { apiRequest } from "../../services/api";

export function getSprints(projectId) {
  const query = projectId ? `?project=${encodeURIComponent(projectId)}` : "";
  return apiRequest(`/sprints/${query}`);
}

export function createSprint(data) {
  return apiRequest("/sprints/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateSprint(sprintId, data) {
  return apiRequest(`/sprints/${sprintId}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteSprint(sprintId) {
  return apiRequest(`/sprints/${sprintId}/`, {
    method: "DELETE",
  });
}
