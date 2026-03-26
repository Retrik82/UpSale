"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { WorkspaceSelector } from "@/components/WorkspaceSelector";
import api from "@/lib/api";
import type { RealCall, ClientTemplate } from "@/types";
import { CallCard } from "@/components/CallCard";
import { getScoreColor } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, token, currentWorkspace, user } = useStore();
  const [calls, setCalls] = useState<RealCall[]>([]);
  const [templates, setTemplates] = useState<ClientTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token && !isAuthenticated) {
      router.push("/login");
      return;
    }

    if (!currentWorkspace) {
      return;
    }

    loadData();
  }, [currentWorkspace, isAuthenticated, token, router]);

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

  if (!currentWorkspace) {
    return <WorkspaceSelector />;
  }

  const completedCalls = calls.filter((c) => c.status === "completed");
  const avgScore =
    completedCalls.length > 0 && completedCalls.some((c) => c.report)
      ? Math.round(
          completedCalls.reduce((acc, c) => acc + (c.report?.overall_score || 0), 0) /
            completedCalls.filter((c) => c.report).length
        )
      : 0;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.full_name?.split(" ")[0] || "there"}
        </h1>
        <p className="text-gray-600 mt-1">Here's how your team is performing</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-xl p-6 border border-gray-200">
          <div className="text-sm text-gray-500 mb-1">Total Calls</div>
          <div className="text-3xl font-bold text-gray-900">{calls.length}</div>
        </div>
        <div className="bg-white rounded-xl p-6 border border-gray-200">
          <div className="text-sm text-gray-500 mb-1">Completed</div>
          <div className="text-3xl font-bold text-green-600">{completedCalls.length}</div>
        </div>
        <div className="bg-white rounded-xl p-6 border border-gray-200">
          <div className="text-sm text-gray-500 mb-1">Average Score</div>
          <div className={`text-3xl font-bold ${getScoreColor(avgScore)}`}>
            {avgScore > 0 ? `${avgScore}/100` : "N/A"}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Recent Calls</h2>
            <button
              onClick={() => router.push("/calls")}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              View all
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : calls.length > 0 ? (
            <div className="space-y-3">
              {calls.slice(0, 5).map((call) => (
                <CallCard
                  key={call.id}
                  call={call}
                  onClick={() => router.push(`/calls/${call.id}`)}
                />
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-xl p-8 border border-gray-200 text-center">
              <p className="text-gray-500">No calls recorded yet</p>
              <button
                onClick={() => router.push("/calls")}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Record Your First Call
              </button>
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Client Templates</h2>
            <button
              onClick={() => router.push("/calls")}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Manage
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : templates.length > 0 ? (
            <div className="space-y-3">
              {templates.slice(0, 5).map((template) => (
                <div
                  key={template.id}
                  className="bg-white rounded-xl p-4 border border-gray-200"
                >
                  <div className="font-medium text-gray-900">{template.name}</div>
                  {template.industry && (
                    <div className="text-sm text-gray-500 mt-1">{template.industry}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-xl p-8 border border-gray-200 text-center">
              <p className="text-gray-500">No templates created yet</p>
            </div>
          )}

          <div className="mt-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => router.push("/calls")}
                className="p-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl text-center hover:opacity-90 transition"
              >
                <svg className="w-6 h-6 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
                <span className="font-medium">Record Call</span>
              </button>
              <button
                onClick={() => router.push("/trainer")}
                className="p-4 bg-gradient-to-r from-violet-500 to-violet-600 text-white rounded-xl text-center hover:opacity-90 transition"
              >
                <svg className="w-6 h-6 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="font-medium">Practice</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
