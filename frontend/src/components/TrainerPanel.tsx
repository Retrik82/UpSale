"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import type { TrainerScenario, TrainerSession } from "@/types";
import { ReportCard } from "@/components/ReportCard";
import { useStore } from "@/lib/store";

interface TrainerPanelProps {
  workspaceId: string;
  onSessionUpdated?: () => void;
}

const difficultyStyles: Record<string, string> = {
  Easy: "bg-green-100 text-green-700",
  Medium: "bg-amber-100 text-amber-700",
  Hard: "bg-red-100 text-red-700",
};

const trainerLanguages = [
  { value: "ru", label: "Русский" },
  { value: "en", label: "English" },
];

const difficultyLabels: Record<string, { ru: string; en: string }> = {
  Easy: { ru: "Лёгкий", en: "Easy" },
  Medium: { ru: "Средний", en: "Medium" },
  Hard: { ru: "Сложный", en: "Hard" },
};

export function TrainerPanel({ workspaceId, onSessionUpdated }: TrainerPanelProps) {
  const { appLanguage, setAppLanguage } = useStore();
  const [scenarios, setScenarios] = useState<TrainerScenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [session, setSession] = useState<TrainerSession | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [sending, setSending] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const difficultyLabel = (difficulty: string) => difficultyLabels[difficulty]?.[appLanguage] || difficulty;
  const hasActiveSession = Boolean(session);
  const text = appLanguage === "ru"
    ? {
        levels: "Уровни тренажёра",
        intro: "Выбери сложность, посмотри на что давить в разговоре и запусти звонок.",
        scenario: "Сценарий",
        pressure: "На что давить",
        tips: "Подсказки",
        appLanguage: "Язык приложения",
        appLanguageHint: "Тренер и отчёт будут на выбранном языке.",
        start: "Начать тренировочный звонок",
        starting: "Запуск...",
        workspace: "Рабочая зона тренажёра",
        workspaceHint: "Проведи тренировочный разговор и после завершения получи автоматический отчёт с оценкой.",
        emptyState: "Выбери уровень слева и начни ролевой разговор.",
        live: "Тренировочный звонок",
        acting: "играет роль клиента.",
        language: "Язык",
        ended: "Разговор завершён",
        endCall: "Закончить звонок",
        finishing: "Завершение...",
        newSession: "Новая сессия",
        placeholder: "Напиши ответ клиенту...",
        sending: "Отправка...",
        send: "Отправить",
        loadError: "Не удалось загрузить сценарии тренажёра.",
        startError: "Не удалось начать сессию.",
        sendError: "Не удалось отправить сообщение.",
        finishError: "Не удалось завершить сессию.",
        reportPending: "Генерируем итоговый отчёт...",
      }
    : {
        levels: "AI Trainer Levels",
        intro: "Pick a difficulty, review the pressure points, and start the call.",
        scenario: "Scenario",
        pressure: "What To Push On",
        tips: "Coach Tips",
        appLanguage: "App Language",
        appLanguageHint: "The trainer and the report will use the selected language.",
        start: "Start Training Call",
        starting: "Starting...",
        workspace: "Trainer Workspace",
        workspaceHint: "Run a practice conversation and get an automatic report with a scorecard when it ends.",
        emptyState: "Choose a difficulty on the left and start the role-play.",
        live: "Live Training Call",
        acting: "is acting as the client.",
        language: "Language",
        ended: "Session ended",
        endCall: "End Call",
        finishing: "Finishing...",
        newSession: "New Session",
        placeholder: "Type your reply to the client...",
        sending: "Sending...",
        send: "Send",
        loadError: "Failed to load trainer scenarios.",
        startError: "Failed to start trainer session.",
        sendError: "Failed to send message.",
        finishError: "Failed to finish session.",
        reportPending: "Generating the final report...",
      };

  useEffect(() => {
    void loadScenarios();
  }, [workspaceId, appLanguage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages.length]);

  useEffect(() => {
    if (!session || session.status !== "completed" || session.report) {
      return;
    }

    let cancelled = false;

    const refreshSession = async () => {
      try {
        const response = await api.get<TrainerSession>(`/trainer/sessions/${session.id}`);
        if (!cancelled) {
          setSession(response.data);
          onSessionUpdated?.();
        }
      } catch {
        if (!cancelled) {
          setError(text.finishError);
        }
      }
    };

    void refreshSession();
    const intervalId = window.setInterval(() => {
      void refreshSession();
    }, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [onSessionUpdated, session, text.finishError]);

  const selectedScenario = useMemo(() => {
    const activeScenarioId = session?.scenario_id ?? selectedScenarioId;
    return scenarios.find((scenario) => scenario.id === activeScenarioId) ?? null;
  }, [scenarios, selectedScenarioId, session?.scenario_id]);

  const loadScenarios = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get<TrainerScenario[]>(`/trainer/scenarios?workspace_id=${workspaceId}&language=${appLanguage}`);
      setScenarios(response.data);
      setSelectedScenarioId((currentId) => {
        if (currentId && response.data.some((scenario) => scenario.id === currentId)) {
          return currentId;
        }

        return response.data[0]?.id ?? null;
      });
    } catch (loadError) {
      const apiError = loadError as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || text.loadError);
    } finally {
      setLoading(false);
    }
  };

  const startSession = async () => {
    if (!selectedScenarioId) {
      return;
    }

    try {
      setStarting(true);
      setError(null);
      const response = await api.post<TrainerSession>("/trainer/sessions", {
        workspace_id: workspaceId,
        scenario_id: selectedScenarioId,
        language: appLanguage,
      });
      setSession(response.data);
      onSessionUpdated?.();
      setInput("");
    } catch (startError) {
      const apiError = startError as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || text.startError);
    } finally {
      setStarting(false);
    }
  };

  const sendMessage = async () => {
    if (!session || session.status !== "in_progress" || !input.trim()) {
      return;
    }

    try {
      setSending(true);
      setError(null);
      const response = await api.post<TrainerSession>(`/trainer/sessions/${session.id}/messages`, {
        content: input.trim(),
      });
      setSession(response.data);
      onSessionUpdated?.();
      setInput("");
    } catch (sendError) {
      const apiError = sendError as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || text.sendError);
    } finally {
      setSending(false);
    }
  };

  const finishSession = async () => {
    if (!session || session.status !== "in_progress") {
      return;
    }

    try {
      setFinishing(true);
      setError(null);
      const response = await api.post<TrainerSession>(`/trainer/sessions/${session.id}/finish`, {
        reason: "sales_manager_finished",
      });
      setSession(response.data);
      onSessionUpdated?.();
    } catch (finishError) {
      const apiError = finishError as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || text.finishError);
    } finally {
      setFinishing(false);
    }
  };

  const resetSession = () => {
    setSession(null);
    setInput("");
    setError(null);
  };

  return (
    <div className={`grid gap-6 ${hasActiveSession ? "grid-cols-1" : "xl:grid-cols-[360px_minmax(0,1fr)]"}`}>
      {!hasActiveSession && (
      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="mb-5">
          <h2 className="text-xl font-bold text-gray-900">{text.levels}</h2>
          <p className="mt-2 text-sm text-gray-600">
            {text.intro}
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center py-10">
            <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="space-y-3">
            {scenarios.map((scenario) => (
              <button
                key={scenario.id}
                onClick={() => setSelectedScenarioId(scenario.id)}
                className={`w-full rounded-2xl border p-4 text-left transition ${
                  selectedScenarioId === scenario.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-blue-300"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-gray-900">{scenario.title}</div>
                    <div className="mt-1 text-sm text-gray-500">
                      {scenario.trainer_name} from {scenario.company_name}
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      difficultyStyles[scenario.difficulty] || "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {difficultyLabel(scenario.difficulty)}
                  </span>
                </div>
                <p className="mt-3 text-sm text-gray-600">{scenario.summary}</p>
              </button>
            ))}
          </div>
        )}

        {selectedScenario && (
          <div className="mt-6 space-y-5 rounded-2xl border border-gray-200 bg-gray-50 p-5">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{text.scenario}</div>
              <p className="mt-2 text-sm text-gray-700">{selectedScenario.scenario}</p>
            </div>

            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{text.pressure}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {selectedScenario.pressure_points.map((point) => (
                  <span key={point} className="rounded-full bg-white px-3 py-1 text-xs text-gray-700">
                    {point}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{text.tips}</div>
              <ul className="mt-3 space-y-2 text-sm text-gray-700">
                {selectedScenario.advice.map((tip) => (
                  <li key={tip} className="rounded-xl bg-white px-3 py-2">
                    {tip}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500" htmlFor="trainer-language">
                {text.appLanguage}
              </label>
              <select
                id="trainer-language"
                value={appLanguage}
                onChange={(event) => setAppLanguage(event.target.value as "ru" | "en")}
                disabled={Boolean(session)}
                className="mt-3 w-full rounded-xl border border-gray-300 bg-white px-3 py-3 text-sm text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              >
                {trainerLanguages.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-500">{text.appLanguageHint}</p>
            </div>

            {!session && (
              <button
                onClick={startSession}
                disabled={starting || !selectedScenarioId}
                className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-3 font-medium text-white transition hover:opacity-90 disabled:opacity-50"
              >
                {starting ? text.starting : text.start}
              </button>
            )}
          </div>
        )}
      </section>
      )}

      <section className="space-y-6">
        {error && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error}
          </div>
        )}

        {!session ? (
          <div className="rounded-2xl border border-gray-200 bg-white p-8">
            <h2 className="text-2xl font-bold text-gray-900">{text.workspace}</h2>
            <p className="mt-3 max-w-2xl text-gray-600">
              {text.workspaceHint}
            </p>
            <div className="mt-6 rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-6 text-sm text-gray-600">
              {text.emptyState}
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-gray-200 bg-gray-50 p-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{text.live}</h2>
                <p className="mt-1 text-sm text-gray-500">
                  {selectedScenario?.trainer_name} {text.acting}
                  {session.language ? ` ${text.language}: ${trainerLanguages.find((item) => item.value === session.language)?.label || session.language}.` : ""}
                  {session.status === "completed" && session.end_reason
                    ? ` ${text.ended}: ${session.end_reason.replaceAll("_", " ")}.`
                    : ""}
                </p>
                {selectedScenario && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${difficultyStyles[selectedScenario.difficulty] || "bg-gray-100 text-gray-700"}`}>
                      {difficultyLabel(selectedScenario.difficulty)}
                    </span>
                    {selectedScenario.pressure_points.slice(0, 3).map((point) => (
                      <span key={point} className="rounded-full bg-white px-3 py-1 text-xs text-gray-700 border border-gray-200">
                        {point}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex gap-3">
                {session.status === "in_progress" ? (
                  <button
                    onClick={finishSession}
                    disabled={finishing}
                    className="rounded-xl border border-red-200 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-50"
                  >
                    {finishing ? text.finishing : text.endCall}
                  </button>
                ) : (
                  <button
                    onClick={resetSession}
                    className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                  >
                    {text.newSession}
                  </button>
                )}
              </div>
            </div>

            <div className="max-h-[520px] space-y-4 overflow-y-auto p-5">
              {session.messages.map((message, index) => (
                <div
                  key={`${message.created_at}-${index}`}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                      message.role === "user"
                        ? "rounded-br-md bg-blue-600 text-white"
                        : "rounded-bl-md bg-gray-100 text-gray-900"
                    }`}
                  >
                    {message.content}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-gray-200 p-5">
              <div className="flex flex-col gap-3 sm:flex-row">
                <input
                  type="text"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void sendMessage();
                    }
                  }}
                  disabled={session.status !== "in_progress" || sending}
                  placeholder={text.placeholder}
                  className="min-w-0 flex-1 rounded-xl border border-gray-300 px-4 py-3 outline-none transition focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                />
                <button
                  onClick={() => void sendMessage()}
                  disabled={session.status !== "in_progress" || sending || !input.trim()}
                  className="rounded-xl bg-blue-600 px-5 py-3 font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
                >
                  {sending ? text.sending : text.send}
                </button>
              </div>
            </div>
          </div>
        )}

        {session && session.status === "completed" && !session.report && (
          <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            {text.reportPending}
          </div>
        )}

        {session?.report && <ReportCard report={session.report} />}
      </section>
    </div>
  );
}
