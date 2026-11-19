import { apiRequest } from "../../services/api";

export async function getProjects() {
  return apiRequest("/projects/");
}

export function createProject(projectData) {
  return apiRequest("/projects/", {
    method: "POST",
    body: JSON.stringify(projectData),
  });
}


export function updateProject(projectId, projectData) {
  return apiRequest(`/projects/${projectId}/edit/`, {
    method: "PATCH",
    body: JSON.stringify(projectData),
  });
}


export function deleteProject(projectId) {
  return apiRequest(`/projects/${projectId}/`, {
    method: "DELETE",
  });
}

export function updateProjectLifecycle(projectId, status) {
  return apiRequest(`/projects/${projectId}/lifecycle/`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}
