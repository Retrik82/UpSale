"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { formatDate } from "@/lib/utils";

export default function AccountPage() {
  const router = useRouter();
  const { user, token, logout, appLanguage, setAppLanguage } = useStore();
  const text = appLanguage === "ru"
    ? {
        title: "Настройки аккаунта",
        profile: "Профиль",
        user: "Пользователь",
        email: "Email",
        fullName: "Полное имя",
        notSet: "Не указано",
        memberSince: "С нами с",
        role: "Роль",
        admin: "Администратор",
        salesManager: "Менеджер продаж",
        language: "Язык",
        languageHint: "Выберите язык приложения для тренажёра и сгенерированных отчётов.",
        danger: "Опасная зона",
        signOutHint: "После выхода вам нужно будет снова войти в аккаунт.",
        signOut: "Выйти",
      }
    : {
        title: "Account Settings",
        profile: "Profile Information",
        user: "User",
        email: "Email",
        fullName: "Full Name",
        notSet: "Not set",
        memberSince: "Member Since",
        role: "Role",
        admin: "Admin",
        salesManager: "Sales Manager",
        language: "Language",
        languageHint: "Choose the app language for the trainer and generated reports.",
        danger: "Danger Zone",
        signOutHint: "Once you sign out, you will need to log in again to access your account.",
        signOut: "Sign Out",
      };

  useEffect(() => {
    if (!token) {
      router.push("/login");
    }
  }, [token, router]);

  if (!user) {
    return null;
  }

  return (
    <div className="p-4 sm:p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">{text.title}</h1>

      <div className="max-w-2xl">
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">{text.profile}</h2>
          </div>

          <div className="p-6 space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-violet-500 rounded-full flex items-center justify-center">
                <span className="text-white text-2xl font-bold">
                  {user.full_name?.charAt(0) || user.email.charAt(0)}
                </span>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {user.full_name || text.user}
                </h3>
                <p className="break-all text-gray-500">{user.email}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 border-t border-gray-100 pt-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm text-gray-500 mb-1">{text.email}</label>
                <p className="break-all text-gray-900">{user.email}</p>
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">{text.fullName}</label>
                <p className="text-gray-900">{user.full_name || text.notSet}</p>
              </div>
              <div className="min-w-0 text-center sm:text-left">
                <label className="block text-sm text-gray-500 mb-1">{text.memberSince}</label>
                <p className="text-gray-900">{formatDate(user.created_at)}</p>
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">{text.role}</label>
                <p className="text-gray-900">
                  {user.system_role === "admin" ? text.admin : text.salesManager}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">{text.language}</h2>
          </div>

          <div className="p-6">
            <p className="mb-4 text-gray-600">{text.languageHint}</p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                onClick={() => setAppLanguage("ru")}
                className={`rounded-lg px-4 py-2 transition ${
                  appLanguage === "ru"
                    ? "bg-blue-600 text-white"
                    : "border border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                Русский
              </button>
              <button
                onClick={() => setAppLanguage("en")}
                className={`rounded-lg px-4 py-2 transition ${
                  appLanguage === "en"
                    ? "bg-blue-600 text-white"
                    : "border border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                English
              </button>
            </div>
          </div>
        </div>

        <div className="mt-8 bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">{text.danger}</h2>
          </div>

          <div className="p-6">
            <p className="text-gray-600 mb-4">{text.signOutHint}</p>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition"
            >
              {text.signOut}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
