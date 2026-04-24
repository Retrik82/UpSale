"use client";

import { getScoreColor, getScoreBgColor, formatScore } from "@/lib/utils";
import type { CallReport } from "@/types";

interface ReportCardProps {
  report: CallReport | null;
}

export function ReportCard({ report }: ReportCardProps) {
  if (!report) {
    return (
      <div className="bg-white rounded-xl p-6 border border-gray-200">
        <p className="text-gray-500 text-center py-8">No report available</p>
      </div>
    );
  }

  const scores = [
    { label: "Engagement", value: report.engagement_score },
    { label: "Objection Handling", value: report.objection_handling_score },
    { label: "Closing", value: report.closing_score },
    { label: "Product Knowledge", value: report.product_knowledge_score },
    { label: "Communication", value: report.communication_clarity_score },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Analysis Report</h3>
          <div
            className={`px-4 py-2 rounded-xl font-bold text-2xl ${getScoreBgColor(
              report.overall_score
            )} ${getScoreColor(report.overall_score)}`}
          >
            {formatScore(report.overall_score)}
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Performance Scores</h4>
          <div className="space-y-3">
            {scores.map((score) => (
              <div key={score.label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">{score.label}</span>
                  <span className={getScoreColor(score.value)}>{formatScore(score.value)}</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      score.value >= 80
                        ? "bg-green-500"
                        : score.value >= 60
                        ? "bg-yellow-500"
                        : "bg-red-500"
                    }`}
                    style={{ width: `${score.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Talk Ratio</h4>
          <div className="flex gap-4 text-sm">
            <div>
              <span className="text-gray-500">Seller: </span>
              <span className="font-medium">{(report.talk_ratio_seller * 100).toFixed(0)}%</span>
            </div>
            <div>
              <span className="text-gray-500">Client: </span>
              <span className="font-medium">{(report.talk_ratio_client * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>

        {report.strengths && report.strengths.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Strengths</h4>
            <ul className="space-y-1">
              {report.strengths.map((strength, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                  <span className="text-green-500">+</span>
                  {strength}
                </li>
              ))}
            </ul>
          </div>
        )}

        {report.areas_for_improvement && report.areas_for_improvement.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Areas for Improvement</h4>
            <ul className="space-y-1">
              {report.areas_for_improvement.map((area, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                  <span className="text-orange-500">-</span>
                  {area}
                </li>
              ))}
            </ul>
          </div>
        )}

        {report.summary && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
            <p className="text-sm text-gray-600">{report.summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}
