"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import api from "@/lib/api";
import type { Workspace } from "@/types";

export function WorkspaceSelector() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  
  const router = useRouter();
  const { currentWorkspace, setCurrentWorkspace, setWorkspaces: setStoreWorkspaces } = useStore();

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    try {
      const response = await api.get<Workspace[]>("/workspaces");
      setWorkspaces(response.data);
      setStoreWorkspaces(response.data);
      
      if (response.data.length > 0 && !currentWorkspace) {
        setCurrentWorkspace(response.data[0]);
      }
    } catch (error) {
      console.error("Failed to load workspaces:", error);
    } finally {
      setLoading(false);
    }
  };

  const createWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await api.post<Workspace>("/workspaces", {
        name: newName,
      });
      setWorkspaces([...workspaces, response.data]);
      setStoreWorkspaces([...workspaces, response.data]);
      setCurrentWorkspace(response.data);
      setNewName("");
      setShowCreate(false);
    } catch (error) {
      console.error("Failed to create workspace:", error);
    }
  };

  const selectWorkspace = (workspace: Workspace) => {
    setCurrentWorkspace(workspace);
    router.push("/dashboard");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Select a Workspace</h2>
          <p className="mt-1 text-gray-600">Choose a workspace to continue</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100">
          {workspaces.length > 0 ? (
            <div className="space-y-3 mb-6">
              {workspaces.map((workspace) => (
                <button
                  key={workspace.id}
                  onClick={() => selectWorkspace(workspace)}
                  className={`w-full p-4 rounded-xl border-2 transition text-left ${
                    currentWorkspace?.id === workspace.id
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 hover:border-blue-300"
                  }`}
                >
                  <div className="font-medium text-gray-900">{workspace.name}</div>
                  {workspace.description && (
                    <div className="text-sm text-gray-500 mt-1">{workspace.description}</div>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 mb-6">
              No workspaces yet. Create one to get started.
            </div>
          )}

          {showCreate ? (
            <form onSubmit={createWorkspace} className="space-y-4">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Workspace name"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                required
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="flex-1 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <button
              onClick={() => setShowCreate(true)}
              className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 hover:border-blue-400 hover:text-blue-600 transition flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Create New Workspace
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
