"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import api from "@/lib/api";
import type { User, AuthToken } from "@/types";

export function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [systemRole, setSystemRole] = useState<"admin" | "sales_manager">("sales_manager");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  
  const router = useRouter();
  const { setAuth, appLanguage } = useStore();
  const text = appLanguage === "ru"
    ? {
        welcomeBack: "С возвращением",
        createAccount: "Создайте аккаунт",
        fullName: "Полное имя",
        role: "Роль",
        salesManager: "Менеджер продаж",
        salesManagerDesc: "Может вступать в несколько рабочих пространств и переключаться между ними.",
        admin: "Администратор",
        adminDesc: "Создаёт рабочие пространства и следит за аналитикой.",
        email: "Email",
        password: "Пароль",
        processing: "Обработка...",
        signIn: "Войти",
        createAccountBtn: "Создать аккаунт",
        noAccount: "Нет аккаунта? Зарегистрируйтесь",
        haveAccount: "Уже есть аккаунт? Войдите",
        error: "Произошла ошибка",
      }
    : {
        welcomeBack: "Welcome back",
        createAccount: "Create your account",
        fullName: "Full Name",
        role: "Role",
        salesManager: "Sales Manager",
        salesManagerDesc: "Join multiple workspaces and switch between them.",
        admin: "Admin",
        adminDesc: "Create workspaces and monitor workspace analytics.",
        email: "Email",
        password: "Password",
        processing: "Processing...",
        signIn: "Sign In",
        createAccountBtn: "Create Account",
        noAccount: "Don't have an account? Sign up",
        haveAccount: "Already have an account? Sign in",
        error: "An error occurred",
      };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        const response = await api.post<AuthToken>("/auth/login", {
          email,
          password,
        });
        localStorage.setItem("access_token", response.data.access_token);
        
        const userResponse = await api.get<User>("/auth/me");
        setAuth(userResponse.data, response.data.access_token);
        router.push("/dashboard");
      } else {
        const response = await api.post<User>("/auth/register", {
          email,
          password,
          full_name: fullName || undefined,
          system_role: systemRole,
        });
        
        const loginResponse = await api.post<AuthToken>("/auth/login", {
          email,
          password,
        });
        localStorage.setItem("access_token", loginResponse.data.access_token);
        setAuth(response.data, loginResponse.data.access_token);
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || text.error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent">
            UpSale
          </h1>
          <p className="mt-2 text-gray-600">
            {isLogin ? text.welcomeBack : text.createAccount}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-5 sm:p-8 border border-gray-100">
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {text.fullName}
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                    placeholder="John Doe"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {text.role}
                  </label>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => setSystemRole("sales_manager")}
                      className={`rounded-xl border p-4 text-left transition ${
                        systemRole === "sales_manager"
                          ? "border-blue-500 bg-blue-50 ring-2 ring-blue-100"
                          : "border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      <div className="font-medium text-gray-900">{text.salesManager}</div>
                      <div className="mt-1 text-sm text-gray-500">{text.salesManagerDesc}</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSystemRole("admin")}
                      className={`rounded-xl border p-4 text-left transition ${
                        systemRole === "admin"
                          ? "border-blue-500 bg-blue-50 ring-2 ring-blue-100"
                          : "border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      <div className="font-medium text-gray-900">{text.admin}</div>
                      <div className="mt-1 text-sm text-gray-500">{text.adminDesc}</div>
                    </button>
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {text.email}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {text.password}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                placeholder="••••••••"
                required
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-violet-600 text-white rounded-lg font-medium hover:opacity-90 transition disabled:opacity-50"
            >
              {loading ? text.processing : isLogin ? text.signIn : text.createAccountBtn}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              {isLogin
                ? text.noAccount
                : text.haveAccount}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
