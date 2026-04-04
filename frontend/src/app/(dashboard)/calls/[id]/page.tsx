"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { TranscriptViewer } from "@/components/TranscriptViewer";
import { ReportCard } from "@/components/ReportCard";
import api from "@/lib/api";
import type { RealCall } from "@/types";
import { formatDate, formatDuration } from "@/lib/utils";
import {
  startBrowserCallRecording,
  type BrowserCallRecorder,
} from "@/lib/browserRecorder";

const RECORDING_START_STORAGE_KEY = "active-call-recording-start";

export default function CallDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useStore();
  const [call, setCall] = useState<RealCall | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [processingMessage, setProcessingMessage] = useState<string | null>(null);
  const [recordingStartedAt, setRecordingStartedAt] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const recorderRef = useRef<BrowserCallRecorder | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }

    loadCall();
  }, [token, params.id, router]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const stored = window.localStorage.getItem(RECORDING_START_STORAGE_KEY);
    if (!stored) {
      return;
    }

    try {
      const parsed = JSON.parse(stored) as { callId?: string; startedAt?: number };
      if (parsed.callId === params.id && typeof parsed.startedAt === "number") {
        setRecordingStartedAt(parsed.startedAt);
      }
    } catch {
      window.localStorage.removeItem(RECORDING_START_STORAGE_KEY);
    }
  }, [params.id]);

  useEffect(() => {
    if (typeof window !== "undefined" && !isRecording) {
      window.localStorage.removeItem(RECORDING_START_STORAGE_KEY);
      setRecordingStartedAt(null);
    }

    if (!isRecording) {
      setElapsedSeconds(0);
      return;
    }

    const startedAt = recordingStartedAt ?? Date.now();
    if (!recordingStartedAt) {
      setRecordingStartedAt(startedAt);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          RECORDING_START_STORAGE_KEY,
          JSON.stringify({ callId: params.id, startedAt })
        );
      }
    }

    const updateElapsed = () => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    };

    updateElapsed();
    const timer = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(timer);
  }, [isRecording, params.id, recordingStartedAt]);

  useEffect(() => {
    return () => {
      if (recorderRef.current) {
        recorderRef.current.cancel().catch(() => undefined);
        recorderRef.current = null;
      }
    };
  }, []);

  const recordingTimerLabel = useMemo(() => formatDuration(elapsedSeconds), [elapsedSeconds]);

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

  const extractError = (error: unknown, fallback: string) => {
    const err = error as Error & { name?: string };
    const apiError = error as { response?: { data?: { detail?: string } } };
    
    if (apiError.response?.data?.detail) {
      return apiError.response.data.detail;
    }
    
    if (err.name === "NotAllowedError" || err.name === "SecurityError") {
      return "Microphone/camera access denied. Recording requires HTTPS or localhost.";
    }
    
    if (err.message?.includes("secure")) {
      return "Recording requires HTTPS. Access from localhost or use HTTPS.";
    }
    
    return err.message || fallback;
  };

  const canTranscribe = Boolean(
    call &&
      call.recording_path &&
      !call.transcript &&
      !isRecording &&
      call.status !== "transcribing"
  );

  const canAnalyze = Boolean(
    call &&
      call.transcript &&
      !call.report &&
      !isRecording &&
      call.status !== "analyzing"
  );

  const handleTranscribe = async () => {
    if (!call) return;
    setActionLoading("transcribe");
    setErrorMessage(null);
    setProcessingMessage("Generating transcript...");
    try {
      await api.post(`/calls/${call.id}/transcribe`, {});
      await loadCall();
    } catch (error) {
      console.error("Failed to transcribe:", error);
      setErrorMessage(extractError(error, "Failed to transcribe the call."));
    } finally {
      setProcessingMessage(null);
      setActionLoading(null);
    }
  };

  const handleAnalyze = async () => {
    if (!call) return;
    setActionLoading("analyze");
    setErrorMessage(null);
    setProcessingMessage("Generating report...");
    try {
      await api.post(`/calls/${call.id}/analyze`);
      await loadCall();
    } catch (error) {
      console.error("Failed to analyze:", error);
      setErrorMessage(extractError(error, "Failed to generate the report."));
    } finally {
      setProcessingMessage(null);
      setActionLoading(null);
    }
  };

  const handleStartRecording = async () => {
    if (!call) return;
    setActionLoading("start-recording");
    setErrorMessage(null);
    setProcessingMessage("Choose the Meet tab and enable tab audio.");
    try {
      const recorder = await startBrowserCallRecording();
      recorderRef.current = recorder;
      const startedAt = Date.now();
      setIsRecording(true);
      setRecordingStartedAt(startedAt);
      setElapsedSeconds(0);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          RECORDING_START_STORAGE_KEY,
          JSON.stringify({ callId: call.id, startedAt })
        );
      }
    } catch (error) {
      console.error("Failed to start recording:", error);
      setErrorMessage(extractError(error, "Failed to start recording."));
    } finally {
      setProcessingMessage(null);
      setActionLoading(null);
    }
  };

  const handleStopRecording = async () => {
    if (!call || !recorderRef.current) return;
    setActionLoading("stop-recording");
    setErrorMessage(null);
    setProcessingMessage("Saving recording...");
    try {
      const audioBlob = await recorderRef.current.stop();
      recorderRef.current = null;
      const formData = new FormData();
      formData.append("file", new File([audioBlob], `${call.id}.wav`, { type: "audio/wav" }));
      const uploadResponse = await api.post<RealCall>(`/calls/${call.id}/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      setCall((current) => (current ? { ...current, ...uploadResponse.data } : uploadResponse.data));
      setIsRecording(false);
      setRecordingStartedAt(null);
      setElapsedSeconds(0);
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(RECORDING_START_STORAGE_KEY);
      }
    } catch (error) {
      console.error("Failed to stop recording:", error);
      setIsRecording(false);
      setErrorMessage(extractError(error, "Failed to stop recording."));
      setProcessingMessage(null);
      setActionLoading(null);
      await loadCall();
      return;
    }

    try {
      setProcessingMessage("Transcribing call...");
      await api.post(`/calls/${call.id}/transcribe`, {});
      await loadCall();
    } catch (error) {
      console.error("Failed to transcribe after stop:", error);
      setErrorMessage(extractError(error, "Recording was saved, but transcription failed."));
      setProcessingMessage(null);
      setActionLoading(null);
      await loadCall();
      return;
    }

    try {
      setProcessingMessage("Building report...");
      await api.post(`/calls/${call.id}/analyze`);
      await loadCall();
    } catch (error) {
      console.error("Failed to analyze after transcription:", error);
      setErrorMessage(extractError(error, "Transcription is ready, but report generation failed."));
      await loadCall();
    } finally {
      setProcessingMessage(null);
      setActionLoading(null);
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
            <h1 title={call.client_name || "Call Details"} className="max-w-3xl truncate text-3xl font-bold text-gray-900">
              {call.client_name || "Call Details"}
            </h1>
            <p className="text-gray-600 mt-1">
              {formatDate(call.created_at)}
              {call.duration_seconds && ` • ${formatDuration(call.duration_seconds)}`}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {!isRecording && !call.recording_path && (
              <button
                onClick={handleStartRecording}
                disabled={actionLoading !== null}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition disabled:opacity-60"
              >
                {actionLoading === "start-recording" ? "Starting..." : "Start Recording"}
              </button>
            )}
            {isRecording && (
              <>
                <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">
                  {recordingTimerLabel}
                </div>
                <button
                  onClick={handleStopRecording}
                  disabled={actionLoading !== null}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-60"
                >
                  {actionLoading === "stop-recording" ? "Processing..." : "Stop Recording"}
                </button>
              </>
            )}
            {canTranscribe && (
              <button
                onClick={handleTranscribe}
                disabled={actionLoading !== null}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                {actionLoading === "transcribe" ? "Transcribing..." : "Transcribe"}
              </button>
            )}
            {canAnalyze && (
              <button
                onClick={handleAnalyze}
                disabled={actionLoading !== null}
                className="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition"
              >
                {actionLoading === "analyze" ? "Analyzing..." : "Analyze"}
              </button>
            )}
          </div>
        </div>
        {errorMessage && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        )}
        {processingMessage && (
          <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">
            {processingMessage}
          </div>
        )}
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
                    : "Start recording to capture and transcribe the call"}
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
