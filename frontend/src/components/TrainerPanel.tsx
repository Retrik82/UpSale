"use client";

import { useState } from "react";
import type { ClientTemplate } from "@/types";

interface TrainerPanelProps {
  templates: ClientTemplate[];
  onStartSimulation: (templateId: string) => void;
}

export function TrainerPanel({ templates, onStartSimulation }: TrainerPanelProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<ClientTemplate | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");

  const handleStart = () => {
    if (selectedTemplate) {
      setIsSimulating(true);
      setMessages([
        {
          role: "assistant",
          content: `Hello! I'm ${selectedTemplate.company_name || "your potential client"}. ${selectedTemplate.description || "Let's discuss your product."}`,
        },
      ]);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages([...messages, userMessage]);
    setInput("");

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Thank you for your response. This is a simulated client response." },
      ]);
    }, 1000);
  };

  const handleEnd = () => {
    setIsSimulating(false);
    setMessages([]);
    setSelectedTemplate(null);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden h-[calc(100vh-200px)]">
      {!isSimulating ? (
        <div className="p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">AI Training Simulator</h2>
          <p className="text-gray-600 mb-6">
            Practice your sales skills with AI-powered role-play scenarios.
          </p>

          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Select a Client Profile</h3>
            <div className="grid gap-3">
              {templates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => setSelectedTemplate(template)}
                  className={`p-4 rounded-xl border-2 text-left transition ${
                    selectedTemplate?.id === template.id
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 hover:border-blue-300"
                  }`}
                >
                  <div className="font-medium text-gray-900">{template.name}</div>
                  {template.industry && (
                    <div className="text-sm text-gray-500">{template.industry}</div>
                  )}
                  {template.pain_points && template.pain_points.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {template.pain_points.slice(0, 3).map((point, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                        >
                          {point}
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleStart}
            disabled={!selectedTemplate}
            className="w-full py-3 bg-gradient-to-r from-blue-600 to-violet-600 text-white rounded-lg font-medium hover:opacity-90 transition disabled:opacity-50"
          >
            Start Simulation
          </button>
        </div>
      ) : (
        <div className="flex flex-col h-full">
          <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">
                {selectedTemplate?.company_name || "Simulation"} - Practice Session
              </h3>
              <p className="text-sm text-gray-500">AI Role-play</p>
            </div>
            <button
              onClick={handleEnd}
              className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition"
            >
              End Session
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message, i) => (
              <div
                key={i}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] px-4 py-3 rounded-2xl ${
                    message.role === "user"
                      ? "bg-blue-600 text-white rounded-br-md"
                      : "bg-gray-100 text-gray-900 rounded-bl-md"
                  }`}
                >
                  {message.content}
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 border-t border-gray-200">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleSend()}
                placeholder="Type your response..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
              <button
                onClick={handleSend}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
