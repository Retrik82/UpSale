"use client";

import { formatDate, formatDuration } from "@/lib/utils";
import type { RealCall } from "@/types";

interface CallCardProps {
  call: RealCall;
  onClick?: () => void;
}

export function CallCard({ call, onClick }: CallCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "recording":
        return "bg-red-100 text-red-700";
      case "completed":
        return "bg-green-100 text-green-700";
      case "failed":
        return "bg-red-100 text-red-700";
      case "transcribing":
      case "analyzing":
        return "bg-yellow-100 text-yellow-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl p-5 border border-gray-200 hover:border-blue-300 hover:shadow-md transition cursor-pointer card-hover"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">
            {call.client_name || "Unnamed Call"}
          </h3>
          <p className="text-sm text-gray-500">{formatDate(call.created_at)}</p>
        </div>
        <span
          className={`px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(
            call.status
          )}`}
        >
          {call.status}
        </span>
      </div>

      {call.duration_seconds && (
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <div className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {formatDuration(call.duration_seconds)}
          </div>
        </div>
      )}

      {call.report && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Overall Score</span>
            <span className="text-lg font-bold text-blue-600">
              {call.report.overall_score}/100
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
