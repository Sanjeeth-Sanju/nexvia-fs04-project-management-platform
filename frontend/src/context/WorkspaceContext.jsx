import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useAuth } from "./AuthContext";
import { createWorkspace as createWorkspaceRequest, deleteWorkspace as deleteWorkspaceRequest } from "../features/workspaces/workspaceService";
import { apiRequest } from "../services/api";

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(
    () => localStorage.getItem("nexvia_selected_workspace_id") || ""
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refreshWorkspaces = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await apiRequest("/workspaces/");
      const data = Array.isArray(response) ? response : response.results || [];

      setWorkspaces(data);
      setSelectedWorkspaceId((currentId) => {
        const stillExists = data.some(
          (workspace) => String(workspace.id) === String(currentId)
        );

        return stillExists ? currentId : String(data[0]?.id || "");
      });

      return data;
    } catch (err) {
      setError(err.message || "Unable to load workspaces.");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;

    if (!isAuthenticated) {
      setWorkspaces([]);
      setSelectedWorkspaceId("");
      setLoading(false);
      setError("");
      return;
    }

    let active = true;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const response = await apiRequest("/workspaces/");
        const data = Array.isArray(response) ? response : response.results || [];

        if (!active) return;

        setWorkspaces(data);
        setSelectedWorkspaceId((currentId) => {
          const stillExists = data.some(
            (workspace) => String(workspace.id) === String(currentId)
          );

          return stillExists ? currentId : String(data[0]?.id || "");
        });
      } catch (err) {
        if (active) {
          setError(err.message || "Unable to load workspaces.");
          setWorkspaces([]);
          setSelectedWorkspaceId("");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    load();

    return () => {
      active = false;
    };
  }, [isAuthenticated, authLoading]);

  useEffect(() => {
    if (selectedWorkspaceId) {
      localStorage.setItem("nexvia_selected_workspace_id", selectedWorkspaceId);
    } else {
      localStorage.removeItem("nexvia_selected_workspace_id");
    }
  }, [selectedWorkspaceId]);

  const selectWorkspace = useCallback((workspaceId) => {
    setSelectedWorkspaceId(String(workspaceId));
  }, []);

  const createWorkspace = useCallback(async (name) => {
    const workspace = await createWorkspaceRequest(name);

    setWorkspaces((current) => [...current, workspace]);
    setSelectedWorkspaceId(String(workspace.id));

    return workspace;
  }, []);

  const removeWorkspace = useCallback(async (workspaceId) => {
    await deleteWorkspaceRequest(workspaceId);

    const remaining = workspaces.filter(
      (workspace) => String(workspace.id) !== String(workspaceId)
    );

    setWorkspaces(remaining);

    if (String(selectedWorkspaceId) === String(workspaceId)) {
      setSelectedWorkspaceId(String(remaining[0]?.id || ""));
    }

    return remaining;
  }, [workspaces, selectedWorkspaceId]);

  const selectedWorkspace = useMemo(
    () =>
      workspaces.find(
        (workspace) => String(workspace.id) === String(selectedWorkspaceId)
      ) || null,
    [workspaces, selectedWorkspaceId]
  );

  const value = useMemo(
    () => ({
      workspaces,
      selectedWorkspace,
      selectedWorkspaceId,
      selectWorkspace,
      createWorkspace,
      deleteWorkspace: removeWorkspace,
      refreshWorkspaces,
      loading,
      error,
    }),
    [
      workspaces,
      selectedWorkspace,
      selectedWorkspaceId,
      selectWorkspace,
      createWorkspace,
      removeWorkspace,
      refreshWorkspaces,
      loading,
      error,
    ]
  );

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);

  if (!context) {
    throw new Error("useWorkspace must be used inside WorkspaceProvider.");
  }

  return context;
}
