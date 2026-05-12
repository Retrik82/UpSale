"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { currentWorkspace, user, logout, setCurrentWorkspace, appLanguage } = useStore();
  const text = appLanguage === "ru"
    ? {
        dashboard: "Панель",
        calls: "Звонки",
        trainer: "Тренажёр",
        account: "Аккаунт",
        workspace: "Рабочее пространство",
        switchWorkspace: "Сменить рабочее пространство",
        user: "Пользователь",
        admin: "Администратор",
        salesManager: "Менеджер продаж",
        signOut: "Выйти",
      }
    : {
        dashboard: "Dashboard",
        calls: "Calls",
        trainer: "Trainer",
        account: "Account",
        workspace: "Workspace",
        switchWorkspace: "Switch workspace",
        user: "User",
        admin: "Admin",
        salesManager: "Sales Manager",
        signOut: "Sign out",
      };
  const navItems = [
    { href: "/dashboard", label: text.dashboard, icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
    ...(user?.system_role === "sales_manager"
      ? [
          { href: "/calls", label: text.calls, icon: "M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" },
          { href: "/trainer", label: text.trainer, icon: "M12 6V4m0 2a6 6 0 016 6m-6-6a6 6 0 00-6 6m12 0a6 6 0 01-6 6m6-6h2m-8 6a6 6 0 01-6-6m6 6v2m0-8H4" },
        ]
      : []),
    { href: "/account", label: text.account, icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" },
  ];

  return (
    <aside className="sticky top-0 z-20 flex w-full shrink-0 flex-col overflow-hidden border-b border-gray-200 bg-white md:h-screen md:w-64 md:border-b-0 md:border-r">
      <div className="p-4 border-b border-gray-200">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-violet-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">SC</span>
          </div>
          <span className="font-bold text-gray-900">UpSale</span>
        </Link>
      </div>

      {currentWorkspace && (
        <div className="hidden border-b border-gray-100 p-4 md:block">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{text.workspace}</div>
          <div className="font-medium text-gray-900">{currentWorkspace.name}</div>
          <button
            onClick={() => {
              setCurrentWorkspace(null);
              router.push("/dashboard");
            }}
            className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            {text.switchWorkspace}
          </button>
        </div>
      )}

      <nav className="flex gap-2 overflow-x-auto p-3 md:flex-1 md:flex-col md:space-y-1 md:overflow-y-auto md:p-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
               "flex shrink-0 items-center gap-3 rounded-lg px-3 py-2 transition",
              pathname === item.href
                ? "bg-blue-50 text-blue-600"
                : "text-gray-600 hover:bg-gray-50"
            )}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
            </svg>
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="hidden border-t border-gray-200 p-4 md:block">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
            <span className="text-gray-600 text-sm font-medium">
              {user?.full_name?.charAt(0) || user?.email?.charAt(0) || "U"}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 truncate">
              {user?.full_name || text.user}
            </div>
            <div className="text-xs text-gray-500 truncate">{user?.email}</div>
            <div className="text-xs uppercase tracking-wide text-gray-400">
              {user?.system_role === "admin" ? text.admin : text.salesManager}
            </div>
          </div>
        </div>
        <button
          onClick={() => {
            logout();
            router.push("/login");
          }}
          className="w-full px-3 py-2 text-left text-gray-600 hover:bg-gray-50 rounded-lg transition flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          {text.signOut}
        </button>
      </div>
    </aside>
  );
}
