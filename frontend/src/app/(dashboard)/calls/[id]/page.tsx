"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import api from "@/lib/api";
import type { RealCall } from "@/types";
import { formatDate, formatDuration } from "@/lib/utils";
import { TranscriptViewer } from "@/components/TranscriptViewer";
import { ReportCard } from "@/components/ReportCard";
import { startBrowserCallRecording, type BrowserCallRecorder } from "@/lib/browserRecorder";

export default function CallDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token, appLanguage } = useStore();
  const text = appLanguage === "ru"
    ? {
        loadError: "Не удалось загрузить детали звонка.",
        saveError: "Не удалось обновить результат звонка.",
        uploadError: "Не удалось загрузить запись и выполнить транскрибацию.",
        notFound: "Звонок не найден",
        back: "Назад к звонкам",
        details: "Детали звонка",
        created: "Создан",
        overview: "Обзор звонка",
        status: "Статус",
        client: "Клиент",
        notSpecified: "Не указан",
        notes: "Заметки",
        noNotes: "Нет заметок",
        outcome: "Результат продажи",
        outcomeHint: "Эта версия backend отслеживает, привёл ли звонок к успешной продаже.",
        current: "Текущий результат",
        completed: "Продажа совершена",
        notCompleted: "Продажа не совершена",
        saving: "Сохранение...",
        recordingInProgress: "Идёт запись...",
        processing: "Обрабатываем запись, готовим транскрибацию и отчёт...",
        recordBlock: "Запись звонка",
        recordCall: "Начать запись",
        stopRecording: "Остановить запись",
        recordHint: "После нажатия выберите вкладку Google Meet, Zoom или окно с созвоном и обязательно включите передачу звука.",
        recordHintExtra: "Если звонок идёт в браузере, выбирайте вкладку и включайте `Share tab audio`. Если звонок в отдельном окне или приложении, включайте системный звук в окне шаринга.",
        timer: "Время звонка",
        transcript: "Транскрипт",
        transcriptHint: "После остановки записи файл сразу загружается, обрабатывается и появляется здесь.",
        report: "Анализ звонка",
        reportHint: "После завершения транскрибации анализ запускается автоматически.",
        markNotCompleted: "Отметить как неуспешно",
        markCompleted: "Отметить как успешно",
        statuses: {
          recording: "Запись",
          completed: "Завершён",
          failed: "Ошибка",
          transcribing: "Расшифровка",
          analyzing: "Анализ",
          pending: "В ожидании",
        } as Record<string, string>,
      }
    : {
        loadError: "Failed to load call details.",
        saveError: "Failed to update sale result.",
        uploadError: "Failed to upload recording and transcribe the call.",
        notFound: "Call not found",
        back: "Back to Calls",
        details: "Call Details",
        created: "Created",
        overview: "Call Overview",
        status: "Status",
        client: "Client",
        notSpecified: "Not specified",
        notes: "Notes",
        noNotes: "No notes",
        outcome: "Sale Outcome",
        outcomeHint: "This backend version tracks whether the call resulted in a successful sale.",
        current: "Current Result",
        completed: "Sale completed",
        notCompleted: "Sale not completed",
        saving: "Saving...",
        recordingInProgress: "Recording in progress...",
        processing: "Processing the recording, transcript, and report...",
        recordBlock: "Call Recording",
        recordCall: "Start Recording",
        stopRecording: "Stop Recording",
        recordHint: "After you start, choose the Google Meet tab, Zoom window, or another call window in the browser picker and make sure audio sharing is enabled.",
        recordHintExtra: "For browser meetings, choose the tab and enable `Share tab audio`. For separate apps or windows, enable system audio in the share dialog.",
        timer: "Call duration",
        transcript: "Transcript",
        transcriptHint: "After you stop recording, the file is uploaded, processed, and shown here.",
        report: "Call Analysis",
        reportHint: "Analysis starts automatically right after transcription completes.",
        markNotCompleted: "Mark as Not Completed",
        markCompleted: "Mark as Completed",
        statuses: {
          recording: "recording",
          completed: "completed",
          failed: "failed",
          transcribing: "transcribing",
          analyzing: "analyzing",
          pending: "pending",
        } as Record<string, string>,
      };
  const [call, setCall] = useState<RealCall | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [recording, setRecording] = useState(false);
  const [processingRecording, setProcessingRecording] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recordingStartedAt, setRecordingStartedAt] = useState<number | null>(null);
  const [recordingElapsedSeconds, setRecordingElapsedSeconds] = useState(0);
  const [lastRecordedSeconds, setLastRecordedSeconds] = useState<number | null>(null);
  const recorderRef = useRef<BrowserCallRecorder | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }

    void loadCall();
  }, [token, params.id, router]);

  useEffect(() => {
    return () => {
      if (recorderRef.current) {
        void recorderRef.current.cancel();
      }
    };
  }, []);

  useEffect(() => {
    if (!recording || recordingStartedAt === null) {
      return;
    }

    const updateElapsed = () => {
      setRecordingElapsedSeconds(Math.max(0, Math.floor((Date.now() - recordingStartedAt) / 1000)));
    };

    updateElapsed();
    const intervalId = window.setInterval(updateElapsed, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [recording, recordingStartedAt]);

  const loadCall = async () => {
    try {
      const response = await api.get<RealCall>(`/calls/${params.id}`);
      setCall(response.data);
      setErrorMessage(null);
    } catch (error) {
      console.error("Failed to load call:", error);
      setErrorMessage(text.loadError);
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
      setErrorMessage(text.saveError);
    } finally {
      setSaving(false);
    }
  };

  const startRecording = async () => {
    if (!call) return;

    try {
      setErrorMessage(null);
      const recorder = await startBrowserCallRecording();
      recorderRef.current = recorder;
      setRecording(true);
      setRecordingStartedAt(Date.now());
      setRecordingElapsedSeconds(0);
      setLastRecordedSeconds(null);
      setCall({ ...call, status: "recording" });
    } catch (error) {
      const message = error instanceof Error ? error.message : text.loadError;
      setErrorMessage(message);
    }
  };

  const stopRecording = async () => {
    if (!call || !recorderRef.current) return;

    const activeRecorder = recorderRef.current;
    const finishedRecordingSeconds = recordingElapsedSeconds;
    recorderRef.current = null;
    setRecording(false);
    setRecordingStartedAt(null);
    setLastRecordedSeconds(finishedRecordingSeconds);
    setProcessingRecording(true);
    setErrorMessage(null);
    setCall({ ...call, status: "transcribing" });

    try {
      const blob = await activeRecorder.stop();
      const formData = new FormData();
      formData.append("file", blob, `call-${call.id}.wav`);

      const response = await api.post<RealCall>(`/calls/${call.id}/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setCall(response.data);
    } catch (error) {
      console.error("Failed to upload recording:", error);
      const apiError = error as { response?: { data?: { detail?: string } } };
      setErrorMessage(apiError.response?.data?.detail || (error instanceof Error ? error.message : text.uploadError));
      await loadCall();
    } finally {
      setProcessingRecording(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4 sm:p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!call) {
    return (
      <div className="p-4 text-center sm:p-8">
        <p className="text-gray-500">{text.notFound}</p>
        <button onClick={() => router.push("/calls")} className="mt-4 text-blue-600">
          {text.back}
        </button>
      </div>
    );
  }

  const displayedDuration = recording
    ? recordingElapsedSeconds
    : Math.round(call.duration_seconds ?? lastRecordedSeconds ?? 0);

  return (
    <div className="p-4 sm:p-8">
      <div className="mb-8">
        <button
          onClick={() => router.push("/calls")}
          className="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          {text.back}
        </button>

        <h1 className="text-3xl font-bold text-gray-900">{call.client_name || text.details}</h1>
        <p className="mt-1 text-gray-600">{text.created} {formatDate(call.created_at)}</p>
      </div>

      {errorMessage && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900">{text.overview}</h2>

          <div className="mt-6 space-y-4 text-sm">
            <div>
              <div className="text-gray-500">{text.status}</div>
              <div className="mt-1 font-medium text-gray-900">{text.statuses[call.status] || call.status}</div>
            </div>
            <div>
              <div className="text-gray-500">{text.client}</div>
              <div className="mt-1 font-medium text-gray-900">{call.client_name || text.notSpecified}</div>
            </div>
            <div>
              <div className="text-gray-500">{text.notes}</div>
              <div className="mt-1 whitespace-pre-wrap text-gray-900">{call.notes || text.noNotes}</div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900">{text.outcome}</h2>
          <p className="mt-2 text-sm text-gray-600">{text.outcomeHint}</p>

          <div className="mt-6 rounded-xl border border-gray-100 bg-gray-50 p-4">
            <div className="text-sm text-gray-500">{text.current}</div>
            <div className={`mt-2 text-2xl font-bold ${call.sale_completed ? "text-green-600" : "text-gray-900"}`}>
              {call.sale_completed ? text.completed : text.notCompleted}
            </div>
          </div>

          <button
            onClick={toggleSaleCompleted}
            disabled={saving}
            className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700 disabled:opacity-60 sm:w-auto"
          >
            {saving
              ? text.saving
              : call.sale_completed
              ? text.markNotCompleted
              : text.markCompleted}
          </button>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900">{text.recordBlock}</h2>
          <p className="mt-2 text-sm text-gray-600">{text.recordHint}</p>
          <p className="mt-2 text-sm text-gray-500">{text.recordHintExtra}</p>

          <div className="mt-5 rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-700">
            <div className="font-medium text-gray-900">{text.status}</div>
            <div className="mt-2">{text.statuses[call.status] || call.status}</div>
            <div className="mt-4 font-medium text-gray-900">{text.timer}</div>
            <div className="mt-2 text-lg font-semibold text-gray-900">{formatDuration(displayedDuration)}</div>
            {recording && <div className="mt-2 text-red-600">{text.recordingInProgress}</div>}
            {processingRecording && <div className="mt-2 text-amber-700">{text.processing}</div>}
          </div>

          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            {!recording ? (
              <button
                onClick={startRecording}
                disabled={processingRecording}
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700 disabled:opacity-60"
              >
                {text.recordCall}
              </button>
            ) : (
              <button
                onClick={stopRecording}
                disabled={processingRecording}
                className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-white transition hover:bg-red-700 disabled:opacity-60"
              >
                {text.stopRecording}
              </button>
            )}
          </div>
        </div>

        <div className="space-y-8">
          <div>
            <div className="mb-3">
              <h2 className="text-lg font-semibold text-gray-900">{text.transcript}</h2>
              <p className="mt-1 text-sm text-gray-600">{text.transcriptHint}</p>
            </div>
            <TranscriptViewer transcript={call.transcript || null} />
          </div>

          <div>
            <div className="mb-3">
              <h2 className="text-lg font-semibold text-gray-900">{text.report}</h2>
              <p className="mt-1 text-sm text-gray-600">{text.reportHint}</p>
            </div>
            <ReportCard report={call.report || null} />
          </div>
        </div>
      </div>
    </div>
  );
}
