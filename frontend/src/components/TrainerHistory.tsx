"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ReportCard } from "@/components/ReportCard";
import { useStore } from "@/lib/store";
import type { TrainerScenario, TrainerSession } from "@/types";

interface TrainerHistoryProps {
  workspaceId: string;
  refreshKey: number;
}

const difficultyLabels: Record<string, { ru: string; en: string }> = {
  Easy: { ru: "Лёгкий", en: "Easy" },
  Medium: { ru: "Средний", en: "Medium" },
  Hard: { ru: "Сложный", en: "Hard" },
};

export function TrainerHistory({ workspaceId, refreshKey }: TrainerHistoryProps) {
  const { appLanguage } = useStore();
  const [sessions, setSessions] = useState<TrainerSession[]>([]);
  const [scenarios, setScenarios] = useState<TrainerScenario[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const text = appLanguage === "ru"
    ? {
        title: "История тренировок",
        intro: "Просматривайте прошлые тренировочные чаты, свои ответы и итоговые выводы.",
        refresh: "Обновить",
        loading: "Загружаем историю...",
        empty: "Истории пока нет. Завершите тренировочный звонок, и он появится здесь.",
        loadError: "Не удалось загрузить историю тренировок.",
        messages: "Переписка",
        report: "Выводы по тренировке",
        noReport: "Отчёт ещё генерируется или пока недоступен.",
        manager: "Вы",
        client: "AI-клиент",
        started: "Начато",
        completed: "Завершено",
        inProgress: "В процессе",
        messageCount: "сообщений",
        select: "Выберите тренировку слева, чтобы посмотреть переписку и выводы.",
      }
    : {
        title: "Training History",
        intro: "Review past training chats, your replies, and final conclusions.",
        refresh: "Refresh",
        loading: "Loading history...",
        empty: "No history yet. Finish a training call and it will appear here.",
        loadError: "Failed to load training history.",
        messages: "Conversation",
        report: "Training Conclusions",
        noReport: "The report is still being generated or is not available yet.",
        manager: "You",
        client: "AI client",
        started: "Started",
        completed: "Completed",
        inProgress: "In progress",
        messageCount: "messages",
        select: "Choose a training session on the left to review the conversation and conclusions.",
      };

  const scenarioMap = useMemo(() => {
    return new Map(scenarios.map((scenario) => [scenario.id, scenario]));
  }, [scenarios]);

  const selectedSession = sessions.find((session) => session.id === selectedSessionId) ?? sessions[0] ?? null;

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [sessionsResponse, scenariosResponse] = await Promise.all([
        api.get<TrainerSession[]>(`/trainer/sessions?workspace_id=${workspaceId}`),
        api.get<TrainerScenario[]>(`/trainer/scenarios?workspace_id=${workspaceId}&language=${appLanguage}`),
      ]);

      setSessions(sessionsResponse.data);
      setScenarios(scenariosResponse.data);
      setSelectedSessionId((currentId) => {
        if (currentId && sessionsResponse.data.some((session) => session.id === currentId)) {
          return currentId;
        }

        return sessionsResponse.data[0]?.id ?? null;
      });
    } catch (loadError) {
      console.error("Failed to load trainer history:", loadError);
      setError(text.loadError);
    } finally {
      setLoading(false);
    }
  }, [appLanguage, text.loadError, workspaceId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory, refreshKey]);

  const getScenarioTitle = (session: TrainerSession) => {
    return scenarioMap.get(session.scenario_id)?.title || session.scenario_id;
  };

  const getScenarioDifficulty = (session: TrainerSession) => {
    const difficulty = scenarioMap.get(session.scenario_id)?.difficulty;
    if (!difficulty) {
      return null;
    }

    return difficultyLabels[difficulty]?.[appLanguage] || difficulty;
  };

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{text.title}</h2>
          <p className="mt-2 max-w-3xl text-sm text-gray-600">{text.intro}</p>
        </div>
        <button
          onClick={() => void loadHistory()}
          className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
        >
          {text.refresh}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-xl border border-dashed border-gray-200 px-4 py-10 text-center text-gray-500">
          {text.loading}
        </div>
      ) : sessions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 px-4 py-10 text-center text-gray-500">
          {text.empty}
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
          <div className="space-y-3">
            {sessions.map((session) => {
              const difficulty = getScenarioDifficulty(session);
              const isSelected = selectedSession?.id === session.id;

              return (
                <button
                  key={session.id}
                  onClick={() => setSelectedSessionId(session.id)}
                  className={`w-full rounded-xl border p-4 text-left transition ${
                    isSelected ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-blue-300"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate font-semibold text-gray-900">{getScenarioTitle(session)}</div>
                      <div className="mt-1 text-xs text-gray-500">
                        {text.started}: {formatDate(session.started_at)}
                      </div>
                    </div>
                    {difficulty && (
                      <span className="shrink-0 rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-gray-700">
                        {difficulty}
                      </span>
                    )}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
                    <span className="rounded-full bg-gray-100 px-2.5 py-1">
                      {session.status === "completed" ? text.completed : text.inProgress}
                    </span>
                    <span className="rounded-full bg-gray-100 px-2.5 py-1">
                      {session.messages.length} {text.messageCount}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {selectedSession ? (
            <div className="space-y-6">
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <div className="text-sm text-gray-500">{text.messages}</div>
                <h3 className="mt-1 text-xl font-semibold text-gray-900">{getScenarioTitle(selectedSession)}</h3>
                <div className="mt-2 text-sm text-gray-600">
                  {text.started}: {formatDate(selectedSession.started_at)}
                  {selectedSession.completed_at ? ` · ${text.completed}: ${formatDate(selectedSession.completed_at)}` : ""}
                </div>
              </div>

              <div className="max-h-[520px] space-y-4 overflow-y-auto rounded-xl border border-gray-200 p-4">
                {selectedSession.messages.map((message, index) => (
                  <div key={`${message.created_at}-${index}`} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm ${
                      message.role === "user"
                        ? "rounded-br-md bg-blue-600 text-white"
                        : "rounded-bl-md bg-gray-100 text-gray-900"
                    }`}
                    >
                      <div className={`mb-1 text-xs font-semibold ${message.role === "user" ? "text-blue-100" : "text-gray-500"}`}>
                        {message.role === "user" ? text.manager : text.client}
                      </div>
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div>
                <h3 className="mb-3 text-lg font-semibold text-gray-900">{text.report}</h3>
                {selectedSession.report ? (
                  <ReportCard report={selectedSession.report} />
                ) : (
                  <div className="rounded-xl border border-dashed border-gray-200 px-4 py-8 text-center text-gray-500">
                    {text.noReport}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-gray-200 px-4 py-10 text-center text-gray-500">
              {text.select}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
