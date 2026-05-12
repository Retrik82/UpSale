"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TrainerPanel } from "@/components/TrainerPanel";
import { TrainerHistory } from "@/components/TrainerHistory";
import { WorkspaceSelector } from "@/components/WorkspaceSelector";
import { useStore } from "@/lib/store";

export default function TrainerPage() {
  const router = useRouter();
  const { token, currentWorkspace, user, appLanguage } = useStore();
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const refreshTrainerHistory = useCallback(() => {
    setHistoryRefreshKey((currentKey) => currentKey + 1);
  }, []);
  const text = appLanguage === "ru"
    ? {
        title: "Тренажёр",
        adminOnly: "Тренажёр доступен только менеджерам продаж. Администратор может сменить рабочее пространство или вернуться на панель.",
        back: "Назад к панели",
        intro: "Тренируйте живые продажи с AI-клиентами, проходите уровни сложности и получайте автоматический отчёт после разговора.",
      }
    : {
        title: "Trainer",
        adminOnly: "The trainer is only available for sales managers. Admins can switch workspaces or go back to the dashboard.",
        back: "Back to Dashboard",
        intro: "Practice live sales conversations with AI clients, escalate through difficulty levels, and review an automatic post-call report.",
      };

  useEffect(() => {
    if (!token) {
      router.push("/login");
    }
  }, [router, token]);

  if (!currentWorkspace) {
    return <WorkspaceSelector />;
  }

  if (user?.system_role === "admin") {
    return (
      <div className="p-8">
        <div className="max-w-2xl rounded-2xl border border-gray-200 bg-white p-8">
          <h1 className="text-3xl font-bold text-gray-900">{text.title}</h1>
          <p className="mt-3 text-gray-600">{text.adminOnly}</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="mt-6 rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700"
          >
            {text.back}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">{text.title}</h1>
        <p className="mt-2 max-w-3xl text-gray-600">{text.intro}</p>
      </div>

      <TrainerPanel
        workspaceId={currentWorkspace.id}
        onSessionUpdated={refreshTrainerHistory}
      />
      <TrainerHistory workspaceId={currentWorkspace.id} refreshKey={historyRefreshKey} />
    </div>
  );
}
