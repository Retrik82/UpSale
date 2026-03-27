"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { WorkspaceSelector } from "@/components/WorkspaceSelector";
import { CallCard } from "@/components/CallCard";
import api from "@/lib/api";
import type { RealCall, ClientTemplate } from "@/types";

const CALL_TITLE_MAX_LENGTH = 255;

export default function CallsPage() {
  const router = useRouter();
  const { token, currentWorkspace } = useStore();
  const [calls, setCalls] = useState<RealCall[]>([]);
  const [templates, setTemplates] = useState<ClientTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCallClientName, setNewCallClientName] = useState("");
  const [newCallTemplate, setNewCallTemplate] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }

    if (!currentWorkspace) {
      return;
    }

    loadData();
  }, [currentWorkspace, token, router]);

  const loadData = async () => {
    if (!currentWorkspace) return;

    try {
      const [callsRes, templatesRes] = await Promise.all([
        api.get<RealCall[]>(`/calls?workspace_id=${currentWorkspace.id}`),
        api.get<ClientTemplate[]>(`/templates?workspace_id=${currentWorkspace.id}`),
      ]);
      setCalls(callsRes.data);
      setTemplates(templatesRes.data);
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      setLoading(false);
    }
  };

  const createCall = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentWorkspace) return;

    try {
      const trimmedName = newCallClientName.trim();
      const response = await api.post<RealCall>("/calls", {
        workspace_id: currentWorkspace.id,
        client_name: trimmedName || undefined,
        client_template_id: newCallTemplate || undefined,
      });
      setCalls([response.data, ...calls]);
      setShowCreateModal(false);
      setNewCallClientName("");
      setNewCallTemplate("");
      setCreateError(null);
      router.push(`/calls/${response.data.id}`);
    } catch (error) {
      console.error("Failed to create call:", error);
      const apiError = error as { response?: { data?: { detail?: string } } };
      setCreateError(apiError.response?.data?.detail || "Failed to create call.");
    }
  };

  if (!currentWorkspace) {
    return <WorkspaceSelector />;
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Calls</h1>
          <p className="text-gray-600 mt-1">Record and analyze your sales calls</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-6 py-3 bg-gradient-to-r from-blue-600 to-violet-600 text-white rounded-lg font-medium hover:opacity-90 transition flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Call
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : calls.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {calls.map((call) => (
            <CallCard
              key={call.id}
              call={call}
              onClick={() => router.push(`/calls/${call.id}`)}
            />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-12 border border-gray-200 text-center">
          <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No calls yet</h3>
          <p className="text-gray-500 mb-6">Start recording your first sales call</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Record Your First Call
          </button>
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md animate-scale-in">
            <h2 className="text-xl font-bold text-gray-900 mb-4">New Call</h2>
            <form onSubmit={createCall} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client Name (optional)
                </label>
                <input
                  type="text"
                  value={newCallClientName}
                  onChange={(e) => setNewCallClientName(e.target.value)}
                  maxLength={CALL_TITLE_MAX_LENGTH}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  placeholder="e.g., Acme Corp"
                />
                <div className="mt-1 flex justify-between text-xs text-gray-500">
                  <span>Up to {CALL_TITLE_MAX_LENGTH} characters</span>
                  <span>{newCallClientName.length}/{CALL_TITLE_MAX_LENGTH}</span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client Template (optional)
                </label>
                <select
                  value={newCallTemplate}
                  onChange={(e) => setNewCallTemplate(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                >
                  <option value="">Select a template</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
              {createError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {createError}
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setCreateError(null);
                  }}
                  className="flex-1 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
                >
                  Create Call
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
