import { apiRequest } from "../../services/api";

export function getIssues() {
  return apiRequest("/issues/");
}

export function createIssue(data) {
  return apiRequest("/issues/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function moveIssue(issueId, data) {
  return apiRequest(`/issues/${issueId}/move/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function getIssue(issueId) {
  return apiRequest(`/issues/${issueId}/`);
}

export function getIssueComments(issueId) {
  return apiRequest(`/issues/${issueId}/comments/`);
}

export function createIssueComment(issueId, body) {
  return apiRequest(`/issues/${issueId}/comments/`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export function getIssueAttachments(issueId) {
  return apiRequest(`/issues/${issueId}/attachments/`);
}

export function uploadIssueAttachment(issueId, file) {
  const data = new FormData();
  data.append("file", file);
  data.append("filename", file.name);

  return apiRequest(`/issues/${issueId}/attachments/`, {
    method: "POST",
    body: data,
  });
}

export function deleteIssueAttachment(attachmentId) {
  return apiRequest(`/attachments/${attachmentId}/`, {
    method: "DELETE",
  });
}

export function updateIssue(issueId, data) {
  return apiRequest(`/issues/${issueId}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteIssue(issueId) {
  return apiRequest(`/issues/${issueId}/`, {
    method: "DELETE",
  });
}
