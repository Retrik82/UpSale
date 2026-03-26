"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { CallCard } from "@/components/CallCard";
import { TranscriptViewer } from "@/components/TranscriptViewer";
import { ReportCard } from "@/components/ReportCard";
import api from "@/lib/api";
import type { RealCall } from "@/types";
import { formatDate, formatDuration } from "@/lib/utils";

export default function CallDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useStore();
  const [call, setCall] = useState<RealCall | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"transcript" | "report">("transcript");

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
    } catch (error) {
      console.error("Failed to load call:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleTranscribe = async () => {
    if (!call) return;
    try {
      await api.post(`/calls/${call.id}/transcribe`);
      loadCall();
    } catch (error) {
      console.error("Failed to transcribe:", error);
    }
  };

  const handleAnalyze = async () => {
    if (!call) return;
    try {
      await api.post(`/calls/${call.id}/analyze`);
      loadCall();
    } catch (error) {
      console.error("Failed to analyze:", error);
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
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Calls
        </button>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {call.client_name || "Call Details"}
            </h1>
            <p className="text-gray-600 mt-1">
              {formatDate(call.created_at)}
              {call.duration_seconds && ` • ${formatDuration(call.duration_seconds)}`}
            </p>
          </div>

          <div className="flex gap-2">
            {call.status === "pending" && !call.transcript && (
              <button
                onClick={handleTranscribe}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Transcribe
              </button>
            )}
            {call.transcript && !call.report && call.status !== "analyzing" && (
              <button
                onClick={handleAnalyze}
                className="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition"
              >
                Analyze
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          {call.transcript ? (
            <TranscriptViewer transcript={call.transcript} />
          ) : (
            <div className="bg-white rounded-xl p-12 border border-gray-200 text-center">
              <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No transcript yet</h3>
              <p className="text-gray-500 mb-4">
                {call.recording_path
                  ? "Click Transcribe to generate the transcript"
                  : "Upload a recording to get started"}
              </p>
            </div>
          )}
        </div>

        <div>
          {call.report ? (
            <ReportCard report={call.report} />
          ) : (
            <div className="bg-white rounded-xl p-12 border border-gray-200 text-center">
              <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No analysis yet</h3>
              <p className="text-gray-500 mb-4">
                {call.transcript
                  ? "Click Analyze to generate the report"
                  : "Transcribe the call first"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
