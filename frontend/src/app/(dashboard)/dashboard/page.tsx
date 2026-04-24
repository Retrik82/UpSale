"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { WorkspaceSelector } from "@/components/WorkspaceSelector";
import api from "@/lib/api";
import type { RealCall, WorkspaceMember, WorkspaceStats } from "@/types";
import { CallCard } from "@/components/CallCard";

type MemberAnalytics = WorkspaceMember & WorkspaceStats;

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, token, currentWorkspace, user } = useStore();
  const [calls, setCalls] = useState<RealCall[]>([]);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [stats, setStats] = useState<WorkspaceStats | null>(null);
  const [memberAnalytics, setMemberAnalytics] = useState<MemberAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoadingUserId, setActionLoadingUserId] = useState<string | null>(null);

  const isAdmin = user?.system_role === "admin";

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
    if (!currentWorkspace || !user) return;

    try {
      setLoading(true);

      if (isAdmin) {
        const [callsRes, membersRes, workspaceStatsRes] = await Promise.all([
          api.get<RealCall[]>(`/calls?workspace_id=${currentWorkspace.id}`),
          api.get<WorkspaceMember[]>(`/workspaces/${currentWorkspace.id}/members`),
          api.get<WorkspaceStats>(`/admin/workspaces/${currentWorkspace.id}/stats`),
        ]);

        const managedMembers = membersRes.data.filter((member) => member.user_id !== user.id);
        const memberStatsResponses = await Promise.all(
          managedMembers.map(async (member) => {
            const response = await api.get<WorkspaceStats>(
              `/admin/workspaces/${currentWorkspace.id}/stats?user_id=${member.user_id}`
            );
            return { ...member, ...response.data };
          })
        );

        setCalls(callsRes.data);
        setMembers(membersRes.data);
        setStats(workspaceStatsRes.data);
        setMemberAnalytics(memberStatsResponses);
      } else {
        const [callsRes, membersRes, myStatsRes] = await Promise.all([
          api.get<RealCall[]>(`/calls?workspace_id=${currentWorkspace.id}`),
          api.get<WorkspaceMember[]>(`/workspaces/${currentWorkspace.id}/members`),
          api.get<WorkspaceStats>(`/workspaces/${currentWorkspace.id}/my-stats`),
        ]);

        setCalls(callsRes.data);
        setMembers(membersRes.data);
        setStats(myStatsRes.data);
        setMemberAnalytics([]);
      }
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const removeMember = async (targetUserId: string) => {
    if (!currentWorkspace) return;

    try {
      setActionLoadingUserId(targetUserId);
      await api.post(`/admin/workspaces/${currentWorkspace.id}/members/${targetUserId}/remove`);
      await loadData();
    } catch (error) {
      console.error("Failed to remove member:", error);
    } finally {
      setActionLoadingUserId(null);
    }
  };

  const removeAndBlockMember = async (targetUserId: string) => {
    if (!currentWorkspace) return;

    try {
      setActionLoadingUserId(targetUserId);
      await api.post(`/admin/workspaces/${currentWorkspace.id}/members/${targetUserId}/remove-and-block`);
      await loadData();
    } catch (error) {
      console.error("Failed to remove and block member:", error);
    } finally {
      setActionLoadingUserId(null);
    }
  };

  if (!currentWorkspace) {
    return <WorkspaceSelector />;
  }

  const totalCalls = stats?.total_calls ?? 0;
  const totalSuccessfulSales = stats?.successful_sales ?? 0;
  const conversionRate = Math.round(stats?.conversion_rate ?? 0);
  const totalMembers = stats?.total_members ?? members.length;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.full_name?.split(" ")[0] || "there"}
        </h1>
        <p className="mt-1 text-gray-600">
          {isAdmin
            ? "Create workspaces, monitor people inside them, and manage access."
            : "See your own results in this workspace and the teammates who are here with you."}
        </p>
      </div>

      <div className={`mb-8 grid grid-cols-1 gap-6 ${isAdmin ? "md:grid-cols-4" : "md:grid-cols-3"}`}>
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <div className="mb-1 text-sm text-gray-500">{isAdmin ? "Workspace Calls" : "My Calls"}</div>
          <div className="text-3xl font-bold text-gray-900">{totalCalls}</div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <div className="mb-1 text-sm text-gray-500">{isAdmin ? "Successful Sales" : "My Sales"}</div>
          <div className="text-3xl font-bold text-green-600">{totalSuccessfulSales}</div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <div className="mb-1 text-sm text-gray-500">Conversion Rate</div>
          <div className="text-3xl font-bold text-blue-600">{conversionRate}%</div>
        </div>
        {isAdmin && (
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="mb-1 text-sm text-gray-500">People in Workspace</div>
            <div className="text-3xl font-bold text-violet-600">{totalMembers}</div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-8">
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                {isAdmin ? "Workspace Call Feed" : "My Recent Calls"}
              </h2>
              {!isAdmin && (
                <button
                  onClick={() => router.push("/calls")}
                  className="text-sm font-medium text-blue-600 hover:text-blue-700"
                >
                  View all
                </button>
              )}
            </div>

            {loading ? (
              <div className="flex justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"></div>
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
              <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
                <p className="text-gray-500">
                  {isAdmin
                    ? "Sales managers have not logged any calls in this workspace yet."
                    : "You have not created any calls in this workspace yet."}
                </p>
                {!isAdmin && (
                  <button
                    onClick={() => router.push("/calls")}
                    className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700"
                  >
                    Open Calls
                  </button>
                )}
              </div>
            )}
          </div>

          {isAdmin && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-xl font-semibold text-gray-900">People Analytics</h2>
              <p className="mt-1 text-sm text-gray-600">
                Remove a person from the workspace or remove them and block the account.
              </p>

              <div className="mt-6 space-y-4">
                {memberAnalytics.length > 0 ? (
                  memberAnalytics.map((member) => (
                    <div key={member.user_id} className="rounded-xl border border-gray-200 p-4">
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <div className="font-medium text-gray-900">{member.full_name || member.email}</div>
                          <div className="mt-1 text-sm text-gray-500">{member.email}</div>
                          <div className="mt-1 text-xs uppercase tracking-wide text-gray-400">{member.role}</div>
                        </div>

                        <div className="grid grid-cols-3 gap-3 text-sm lg:min-w-[320px]">
                          <div className="rounded-lg bg-gray-50 px-3 py-2">
                            <div className="text-gray-500">Calls</div>
                            <div className="font-semibold text-gray-900">{member.total_calls}</div>
                          </div>
                          <div className="rounded-lg bg-gray-50 px-3 py-2">
                            <div className="text-gray-500">Sales</div>
                            <div className="font-semibold text-gray-900">{member.successful_sales}</div>
                          </div>
                          <div className="rounded-lg bg-gray-50 px-3 py-2">
                            <div className="text-gray-500">Conv.</div>
                            <div className="font-semibold text-gray-900">{Math.round(member.conversion_rate)}%</div>
                          </div>
                        </div>

                        <div className="flex gap-3">
                          <button
                            onClick={() => removeMember(member.user_id)}
                            disabled={actionLoadingUserId === member.user_id}
                            className="rounded-lg border border-amber-300 px-4 py-2 text-sm font-medium text-amber-700 transition hover:bg-amber-50 disabled:opacity-50"
                          >
                            Remove
                          </button>
                          <button
                            onClick={() => removeAndBlockMember(member.user_id)}
                            disabled={actionLoadingUserId === member.user_id}
                            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-50"
                          >
                            Remove + Block
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-xl border border-dashed border-gray-200 px-4 py-8 text-center text-gray-500">
                    No other people in this workspace yet.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-8">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-gray-900">
              {isAdmin ? "Workspace Members" : "People in Workspace"}
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              {isAdmin
                ? "See everyone currently attached to this workspace."
                : "You can only see who is in this workspace."}
            </p>

            <div className="mt-4 space-y-3">
              {members.map((member) => (
                <div key={member.id} className="rounded-lg border border-gray-200 px-4 py-3">
                  <div className="font-medium text-gray-900">{member.full_name || member.email}</div>
                  {isAdmin && (
                    <div className="mt-1 text-xs uppercase tracking-wide text-gray-400">{member.role}</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-gray-900">Quick Actions</h2>
            <p className="mt-1 text-sm text-gray-600">
              {isAdmin
                ? "Admins manage workspaces and people from the dashboard."
                : "Sales managers can open calls and review their own performance."}
            </p>

            <div className="mt-6 space-y-3">
              {!isAdmin && (
                <button
                  onClick={() => router.push("/calls")}
                  className="w-full rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 p-4 text-left text-white transition hover:opacity-90"
                >
                  <div className="font-medium">Open Calls</div>
                  <div className="mt-1 text-sm text-blue-100">Create and manage only your own calls.</div>
                </button>
              )}
              <button
                onClick={() => router.push("/account")}
                className="w-full rounded-xl border border-gray-200 p-4 text-left transition hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="font-medium text-gray-900">View Account</div>
                <div className="mt-1 text-sm text-gray-600">Check your profile and current role.</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
