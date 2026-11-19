import { apiRequest } from "../../services/api";

export async function getDashboardData() {
  const [workspaces, projects, issues] = await Promise.all([
    apiRequest("/workspaces/"),
    apiRequest("/projects/"),
    apiRequest("/issues/"),
  ]);

  const workspaceList = Array.isArray(workspaces)
    ? workspaces
    : workspaces.results || [];

  const projectList = Array.isArray(projects)
    ? projects
    : projects.results || [];

  const issueList = Array.isArray(issues)
    ? issues
    : issues.results || [];

  return {
    workspaces: workspaceList,
    projects: projectList,
    issues: issueList,
  };
}

export async function getWorkspaceActivity(workspaceId) {
  const data = await apiRequest(
    `/workspaces/${workspaceId}/audit-logs/`
  );

  return Array.isArray(data) ? data : data.results || [];
}

export async function getWorkspaceWorkflowStatuses(workspaceId) {
  const data = await apiRequest(
    `/workspaces/${workspaceId}/workflow-statuses/`
  );

  return Array.isArray(data) ? data : data.results || [];
}
