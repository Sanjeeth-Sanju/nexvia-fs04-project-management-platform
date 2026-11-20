import { apiRequest } from "../../services/api";

export const getNotifications = () =>
  apiRequest("/notifications/");

export const markNotificationRead = (id) =>
  apiRequest(`/notifications/${id}/read/`, { method: "PATCH" });

export const markAllNotificationsRead = () =>
  apiRequest("/notifications/read-all/", { method: "POST" });

export const deleteNotification = (id) =>
  apiRequest(`/notifications/${id}/`, { method: "DELETE" });

export const clearAllNotifications = () =>
  apiRequest("/notifications/clear-all/", { method: "DELETE" });
