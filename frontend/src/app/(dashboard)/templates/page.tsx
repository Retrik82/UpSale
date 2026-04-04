"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import { WorkspaceSelector } from "@/components/WorkspaceSelector";
import api from "@/lib/api";
import type { ClientTemplate } from "@/types";

export default function TemplatesPage() {
  const router = useRouter();
  const { token, currentWorkspace } = useStore();
  const [templates, setTemplates] = useState<ClientTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    company_name: "",
    industry: "",
    pain_points: "",
    objections: "",
    talking_points: "",
    preferred_tone: "professional",
  });

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
  }, [token, router]);

  useEffect(() => {
    if (currentWorkspace) {
      loadTemplates();
    }
  }, [currentWorkspace]);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentWorkspace) return;

    try {
      await api.post("/templates", {
        workspace_id: currentWorkspace.id,
        name: form.name,
        description: form.description || null,
        company_name: form.company_name || null,
        industry: form.industry || null,
        pain_points: form.pain_points ? form.pain_points.split(",").map(s => s.trim()).filter(Boolean) : [],
        objections: form.objections ? form.objections.split(",").map(s => s.trim()).filter(Boolean) : [],
        talking_points: form.talking_points ? form.talking_points.split(",").map(s => s.trim()).filter(Boolean) : [],
        preferred_tone: form.preferred_tone,
      });
      setShowForm(false);
      setForm({ name: "", description: "", company_name: "", industry: "", pain_points: "", objections: "", talking_points: "", preferred_tone: "professional" });
      loadTemplates();
    } catch (error) {
      console.error("Failed to create template:", error);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this template?")) return;
    try {
      await api.delete(`/templates/${id}`);
      loadTemplates();
    } catch (error) {
      console.error("Failed to delete template:", error);
    }
  };

  if (!currentWorkspace) {
    return <WorkspaceSelector />;
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Client Templates</h1>
          <p className="text-gray-600 mt-1">Create profiles for AI training simulations</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          {showForm ? "Cancel" : "Create Template"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Budget Enterprise CEO"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
              <input
                type="text"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Acme Corp"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={2}
                placeholder="A Fortune 500 company looking to optimize their sales process..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
              <input
                type="text"
                value={form.industry}
                onChange={(e) => setForm({ ...form, industry: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="SaaS, Healthcare, Finance..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Tone</label>
              <select
                value={form.preferred_tone}
                onChange={(e) => setForm({ ...form, preferred_tone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="professional">Professional</option>
                <option value="friendly">Friendly</option>
                <option value="formal">Formal</option>
                <option value="casual">Casual</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Pain Points (comma-separated)</label>
              <input
                type="text"
                value={form.pain_points}
                onChange={(e) => setForm({ ...form, pain_points: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="High turnover, Slow onboarding, Budget constraints"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Objections (comma-separated)</label>
              <input
                type="text"
                value={form.objections}
                onChange={(e) => setForm({ ...form, objections: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Too expensive, Not enough time, Need to talk to my team"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Talking Points (comma-separated)</label>
              <input
                type="text"
                value={form.talking_points}
                onChange={(e) => setForm({ ...form, talking_points: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="ROI Calculator, Free trial, Case studies"
              />
            </div>
          </div>
          <button
            type="submit"
            className="mt-4 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
          >
            Create Template
          </button>
        </form>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : templates.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No templates yet. Create one to start training.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {templates.map((template) => (
            <div key={template.id} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">{template.name}</h3>
                  {template.company_name && (
                    <p className="text-sm text-gray-500">{template.company_name}</p>
                  )}
                  {template.industry && (
                    <span className="inline-block mt-2 px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                      {template.industry}
                    </span>
                  )}
                  {template.description && (
                    <p className="mt-2 text-sm text-gray-600">{template.description}</p>
                  )}
                  {template.pain_points && template.pain_points.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {template.pain_points.map((point, i) => (
                        <span key={i} className="px-2 py-0.5 bg-red-50 text-red-600 rounded text-xs">
                          {point}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(template.id)}
                  className="ml-4 px-3 py-1 text-red-600 hover:bg-red-50 rounded transition text-sm"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
