"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import api from "@/lib/api";
import type { RealCall } from "@/types";
import { formatDate } from "@/lib/utils";

export default function CallDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useStore();
  const [call, setCall] = useState<RealCall | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }

    loadCall();
  }, [token, params.id, router]);

  const loadCall = async () => {
    try {
      const response = await api.get<RealCall>(`/calls/${params.id}`);
      setCall(response.data);
      setErrorMessage(null);
    } catch (error) {
      console.error("Failed to load call:", error);
      setErrorMessage("Failed to load call details.");
    } finally {
      setLoading(false);
    }
  };

  const toggleSaleCompleted = async () => {
    if (!call) return;

    setSaving(true);
    setErrorMessage(null);

    try {
      const response = await api.patch<RealCall>(`/calls/${call.id}/sale-completed`, {
        sale_completed: !call.sale_completed,
      });
      setCall(response.data);
    } catch (error) {
      console.error("Failed to update call:", error);
      setErrorMessage("Failed to update sale result.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!call) {
    return (
      <div className="p-8 text-center">
        <p className="text-gray-500">Call not found</p>
        <button onClick={() => router.push("/calls")} className="mt-4 text-blue-600">
          Back to Calls
        </button>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <button
          onClick={() => router.push("/calls")}
          className="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Calls
        </button>

        <h1 className="text-3xl font-bold text-gray-900">{call.client_name || "Call Details"}</h1>
        <p className="mt-1 text-gray-600">Created {formatDate(call.created_at)}</p>
      </div>

      {errorMessage && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900">Call Overview</h2>

          <div className="mt-6 space-y-4 text-sm">
            <div>
              <div className="text-gray-500">Status</div>
              <div className="mt-1 font-medium text-gray-900">{call.status}</div>
            </div>
            <div>
              <div className="text-gray-500">Client</div>
              <div className="mt-1 font-medium text-gray-900">{call.client_name || "Not specified"}</div>
            </div>
            <div>
              <div className="text-gray-500">Notes</div>
              <div className="mt-1 whitespace-pre-wrap text-gray-900">{call.notes || "No notes"}</div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900">Sale Outcome</h2>
          <p className="mt-2 text-sm text-gray-600">
            This backend version tracks whether the call resulted in a successful sale.
          </p>

          <div className="mt-6 rounded-xl border border-gray-100 bg-gray-50 p-4">
            <div className="text-sm text-gray-500">Current Result</div>
            <div className={`mt-2 text-2xl font-bold ${call.sale_completed ? "text-green-600" : "text-gray-900"}`}>
              {call.sale_completed ? "Sale completed" : "Sale not completed"}
            </div>
          </div>

          <button
            onClick={toggleSaleCompleted}
            disabled={saving}
            className="mt-6 rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700 disabled:opacity-60"
          >
            {saving
              ? "Saving..."
              : call.sale_completed
              ? "Mark as Not Completed"
              : "Mark as Completed"}
          </button>
        </div>
      </div>
    </div>
  );
}
