"use client";

import type { Transcript } from "@/types";

interface TranscriptViewerProps {
  transcript: Transcript | null;
}

export function TranscriptViewer({ transcript }: TranscriptViewerProps) {
  if (!transcript) {
    return (
      <div className="bg-white rounded-xl p-6 border border-gray-200">
        <p className="text-gray-500 text-center py-8">No transcript available</p>
      </div>
    );
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getSpeakerColor = (speaker: string) => {
    const colors = [
      "bg-blue-100 text-blue-800 border-blue-200",
      "bg-violet-100 text-violet-800 border-violet-200",
      "bg-emerald-100 text-emerald-800 border-emerald-200",
      "bg-amber-100 text-amber-800 border-amber-200",
    ];
    const hash = speaker.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Transcript</h3>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span>{transcript.language}</span>
            {transcript.speakers && (
              <span>{transcript.speakers.length} speakers</span>
            )}
          </div>
        </div>
      </div>

      <div className="max-h-96 overflow-y-auto p-4 space-y-4">
        {transcript.segments.map((segment, index) => (
          <div key={index} className="flex gap-3">
            <div className="flex-shrink-0 w-12 text-xs text-gray-400 pt-1">
              {formatTime(segment.start)}
            </div>
            <div className="flex-1">
              <span
                className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${getSpeakerColor(
                  segment.speaker
                )}`}
              >
                {segment.speaker}
              </span>
              <p className="mt-1 text-gray-700">{segment.text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
