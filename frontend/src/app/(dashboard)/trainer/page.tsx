"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { WorkspaceSelector } from "@/components/WorkspaceSelector";
import { TrainerPanel } from "@/components/TrainerPanel";
import api from "@/lib/api";
import type { ClientTemplate } from "@/types";

export default function TrainerPage() {
  const router = useRouter();
  const { token, currentWorkspace } = useStore();
  const [templates, setTemplates] = useState<ClientTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }

    if (!currentWorkspace) {
      return;
    }

    loadTemplates();
  }, [currentWorkspace, token, router]);

  const loadTemplates = async () => {
    if (!currentWorkspace) return;

    try {
      const response = await api.get<ClientTemplate[]>(
        `/templates?workspace_id=${currentWorkspace.id}`
      );
      setTemplates(response.data);
    } catch (error) {
      console.error("Failed to load templates:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartSimulation = async (templateId: string): Promise<string | null> => {
    console.log("handleStartSimulation called", { templateId, currentWorkspace });
    if (!currentWorkspace) return null;

    try {
      const response = await api.post("/simulations", {
        workspace_id: currentWorkspace.id,
        name: `Simulation - ${new Date().toLocaleDateString()}`,
        client_template_id: templateId,
      });
      console.log("Simulation created:", response.data);
      await api.post(`/simulations/${response.data.id}/start`);
      console.log("Simulation started");
      return response.data.id;
    } catch (error) {
      console.error("Failed to start simulation:", error);
      return null;
    }
  };

  if (!currentWorkspace) {
    return <WorkspaceSelector />;
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">AI Training Simulator</h1>
        <p className="text-gray-600 mt-1">
          Practice your sales skills with AI-powered role-play scenarios
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <TrainerPanel templates={templates} onStartSimulation={handleStartSimulation} />
      )}
    </div>
  );
}
