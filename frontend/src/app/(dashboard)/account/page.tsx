"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { formatDate } from "@/lib/utils";

export default function AccountPage() {
  const router = useRouter();
  const { user, token, logout } = useStore();

  useEffect(() => {
    if (!token) {
      router.push("/login");
    }
  }, [token, router]);

  if (!user) {
    return null;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Account Settings</h1>

      <div className="max-w-2xl">
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Profile Information</h2>
          </div>

          <div className="p-6 space-y-6">
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-violet-500 rounded-full flex items-center justify-center">
                <span className="text-white text-2xl font-bold">
                  {user.full_name?.charAt(0) || user.email.charAt(0)}
                </span>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {user.full_name || "User"}
                </h3>
                <p className="text-gray-500">{user.email}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6 pt-4 border-t border-gray-100">
              <div>
                <label className="block text-sm text-gray-500 mb-1">Email</label>
                <p className="text-gray-900">{user.email}</p>
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">Full Name</label>
                <p className="text-gray-900">{user.full_name || "Not set"}</p>
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">Member Since</label>
                <p className="text-gray-900">{formatDate(user.created_at)}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Danger Zone</h2>
          </div>

          <div className="p-6">
            <p className="text-gray-600 mb-4">
              Once you sign out, you will need to log in again to access your account.
            </p>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
