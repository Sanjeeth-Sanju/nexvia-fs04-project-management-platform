import { apiRequest } from "../../services/api";
export async function getWorkspaceActivity(id) {
  const data = await apiRequest(`/workspaces/${id}/audit-logs/`);
  return Array.isArray(data) ? data : data?.results || [];
}
