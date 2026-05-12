"use client";

import { getScoreColor, getScoreBgColor, formatScore } from "@/lib/utils";
import type { CallReport } from "@/types";
import { useStore } from "@/lib/store";

interface ReportCardProps {
  report: CallReport | null;
}

export function ReportCard({ report }: ReportCardProps) {
  const { appLanguage } = useStore();
  const text = appLanguage === "ru"
    ? {
        empty: "Отчёт пока недоступен",
        title: "Отчёт по разговору",
        scores: "Оценки по навыкам",
        engagement: "Вовлечение",
        objections: "Работа с возражениями",
        closing: "Закрытие на шаг",
        product: "Знание продукта",
        communication: "Ясность коммуникации",
        talkRatio: "Баланс речи",
        seller: "Менеджер",
        client: "Клиент",
        strengths: "Сильные стороны",
        improvements: "Что улучшить",
        summary: "Краткий вывод",
      }
    : {
        empty: "No report available",
        title: "Analysis Report",
        scores: "Performance Scores",
        engagement: "Engagement",
        objections: "Objection Handling",
        closing: "Closing",
        product: "Product Knowledge",
        communication: "Communication",
        talkRatio: "Talk Ratio",
        seller: "Seller",
        client: "Client",
        strengths: "Strengths",
        improvements: "Areas for Improvement",
        summary: "Summary",
      };

  if (!report) {
    return (
      <div className="bg-white rounded-xl p-6 border border-gray-200">
        <p className="text-gray-500 text-center py-8">{text.empty}</p>
      </div>
    );
  }

  const scores = [
    { label: text.engagement, value: report.engagement_score },
    { label: text.objections, value: report.objection_handling_score },
    { label: text.closing, value: report.closing_score },
    { label: text.product, value: report.product_knowledge_score },
    { label: text.communication, value: report.communication_clarity_score },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">{text.title}</h3>
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
          <h4 className="text-sm font-medium text-gray-700 mb-3">{text.scores}</h4>
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
          <h4 className="text-sm font-medium text-gray-700 mb-3">{text.talkRatio}</h4>
          <div className="flex gap-4 text-sm">
            <div>
              <span className="text-gray-500">{text.seller}: </span>
              <span className="font-medium">{(report.talk_ratio_seller * 100).toFixed(0)}%</span>
            </div>
            <div>
              <span className="text-gray-500">{text.client}: </span>
              <span className="font-medium">{(report.talk_ratio_client * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>

        {report.strengths && report.strengths.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">{text.strengths}</h4>
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
            <h4 className="text-sm font-medium text-gray-700 mb-2">{text.improvements}</h4>
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
            <h4 className="text-sm font-medium text-gray-700 mb-2">{text.summary}</h4>
            <p className="text-sm text-gray-600">{report.summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}
