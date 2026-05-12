"use client";

import { useStore } from "@/lib/store";

export function GlobalLanguageSwitcher() {
  const { appLanguage, setAppLanguage } = useStore();

  return (
    <div className="fixed right-4 top-4 z-50 rounded-2xl border border-gray-200 bg-white/90 p-1 shadow-lg backdrop-blur">
      <div className="flex items-center gap-1">
        <button
          onClick={() => setAppLanguage("ru")}
          className={`rounded-xl px-3 py-2 text-sm font-medium transition ${
            appLanguage === "ru" ? "bg-blue-600 text-white" : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          RU
        </button>
        <button
          onClick={() => setAppLanguage("en")}
          className={`rounded-xl px-3 py-2 text-sm font-medium transition ${
            appLanguage === "en" ? "bg-blue-600 text-white" : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          EN
        </button>
      </div>
    </div>
  );
}
