"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";
import api from "@/lib/api";
import type { Workspace, WorkspaceMember } from "@/types";

export function WorkspaceSelector() {
  const [joinedWorkspaces, setJoinedWorkspaces] = useState<Workspace[]>([]);
  const [discoverableWorkspaces, setDiscoverableWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [activeJoinWorkspaceId, setActiveJoinWorkspaceId] = useState<string | null>(null);
  const [joinPassword, setJoinPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const router = useRouter();
  const {
    user,
    currentWorkspace,
    setCurrentWorkspace,
    setWorkspaces: setStoreWorkspaces,
    appLanguage,
  } = useStore();
  const text = appLanguage === "ru"
    ? {
        loadError: "Не удалось загрузить рабочие пространства.",
        createError: "Не удалось создать рабочее пространство.",
        notFound: "Рабочее пространство с таким названием не найдено.",
        leaveError: "Не удалось покинуть рабочее пространство.",
        enterPassword: "Введите пароль рабочего пространства.",
        joinError: "Не удалось присоединиться к рабочему пространству.",
        choose: "Выберите рабочее пространство",
        adminHint: "Создавайте рабочие пространства и открывайте то, которым хотите управлять.",
        salesHint: "Вступайте в рабочие пространства по паролю и переключайтесь между теми, к которым у вас уже есть доступ.",
        findByName: "Найти рабочее пространство по имени",
        startTyping: "Начните вводить название рабочего пространства",
        find: "Найти",
        yourWorkspaces: "Ваши рабочие пространства",
        openMember: "Откройте любое рабочее пространство, в котором вы уже состоите.",
        noneJoined: "Вы ещё не вступили ни в одно рабочее пространство.",
        member: "Участник",
        leave: "Покинуть рабочее пространство",
        createFirstAdmin: "Создайте первое рабочее пространство, чтобы начать управление аналитикой.",
        createFirstSales: "Найдите рабочее пространство по имени или введите пароль, чтобы получить доступ.",
        enterWorkspacePassword: "Введите пароль рабочего пространства, чтобы получить доступ.",
        createWorkspace: "Создать рабочее пространство",
        createWorkspaceHint: "Администраторы задают имя рабочего пространства и пароль для входа.",
        newWorkspace: "Новое рабочее пространство",
        workspaceName: "Название рабочего пространства",
        descriptionOptional: "Описание (необязательно)",
        workspacePassword: "Пароль рабочего пространства",
        create: "Создать",
        cancel: "Отмена",
        available: "Доступные рабочие пространства",
        availableHint: "Найдите рабочее пространство в списке и введите его пароль, чтобы присоединиться.",
        joined: "Вы уже внутри",
        passwordRequired: "Нужен пароль",
        openWorkspace: "Открыть рабочее пространство",
        enterWorkspacePasswordShort: "Введите пароль рабочего пространства",
        joinWorkspace: "Вступить в рабочее пространство",
        enterPasswordButton: "Ввести пароль",
        noWorkspaces: "Рабочие пространства ещё не созданы.",
      }
    : {
        loadError: "Failed to load workspaces.",
        createError: "Failed to create workspace.",
        notFound: "Workspace with this name was not found.",
        leaveError: "Failed to leave workspace.",
        enterPassword: "Enter the workspace password.",
        joinError: "Failed to join workspace.",
        choose: "Choose a Workspace",
        adminHint: "Create workspaces and open the one you want to manage.",
        salesHint: "Join workspaces by password and switch between the ones you already have access to.",
        findByName: "Find workspace by name",
        startTyping: "Start typing a workspace name",
        find: "Find",
        yourWorkspaces: "Your Workspaces",
        openMember: "Open any workspace you are already a member of.",
        noneJoined: "You have not joined any workspaces yet.",
        member: "Member",
        leave: "Leave Workspace",
        createFirstAdmin: "Create your first workspace to start managing analytics.",
        createFirstSales: "Enter a workspace password to get access.",
        enterWorkspacePassword: "Enter a workspace password to get access.",
        createWorkspace: "Create Workspace",
        createWorkspaceHint: "Admins set the workspace name and login password.",
        newWorkspace: "New Workspace",
        workspaceName: "Workspace name",
        descriptionOptional: "Description (optional)",
        workspacePassword: "Workspace password",
        create: "Create",
        cancel: "Cancel",
        available: "Available Workspaces",
        availableHint: "Find a workspace in the list and enter its password to join.",
        joined: "Joined",
        passwordRequired: "Password required",
        openWorkspace: "Open Workspace",
        enterWorkspacePasswordShort: "Enter workspace password",
        joinWorkspace: "Join Workspace",
        enterPasswordButton: "Enter Password",
        noWorkspaces: "No workspaces have been created yet.",
      };

  const isAdmin = user?.system_role === "admin";

  useEffect(() => {
    loadWorkspaces();
  }, [user?.system_role]);

  const loadWorkspaces = async () => {
    setLoading(true);
    setError(null);

    try {
      const joinedResponse = await api.get<Workspace[]>("/workspaces");
      setJoinedWorkspaces(joinedResponse.data);
      setStoreWorkspaces(joinedResponse.data);

      if (isAdmin) {
        setDiscoverableWorkspaces(joinedResponse.data);
      } else {
        const discoverResponse = await api.get<Workspace[]>("/workspaces/discover");
        setDiscoverableWorkspaces(discoverResponse.data);
      }
    } catch (loadError) {
      console.error("Failed to load workspaces:", loadError);
      setError(text.loadError);
    } finally {
      setLoading(false);
    }
  };

  const createWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await api.post<Workspace>("/workspaces", {
        name: newName.trim(),
        description: newDescription.trim() || undefined,
        password: newPassword,
      });

      const updatedWorkspaces = [response.data, ...joinedWorkspaces];
      setJoinedWorkspaces(updatedWorkspaces);
      setDiscoverableWorkspaces(updatedWorkspaces);
      setStoreWorkspaces(updatedWorkspaces);
      setCurrentWorkspace(response.data);
      setNewName("");
      setNewDescription("");
      setNewPassword("");
      setShowCreate(false);
      router.push("/dashboard");
    } catch (createError) {
      console.error("Failed to create workspace:", createError);
      const apiError = createError as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || text.createError);
    }
  };

  const selectWorkspace = (workspace: Workspace) => {
    setCurrentWorkspace(workspace);
    router.push("/dashboard");
  };

  const findWorkspaceByName = () => {
    const normalizedName = searchTerm.trim().toLowerCase();
    if (!normalizedName) {
      return null;
    }

    return discoverableWorkspaces.find(
      (workspace) => workspace.name.trim().toLowerCase() === normalizedName
    ) ?? discoverableWorkspaces.find((workspace) =>
      workspace.name.trim().toLowerCase().includes(normalizedName)
    ) ?? null;
  };

  const openWorkspaceByName = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const matchedWorkspace = findWorkspaceByName();
    if (!matchedWorkspace) {
      setActiveJoinWorkspaceId(null);
      setError(text.notFound);
      return;
    }

    const isMember = matchedWorkspace.is_member || joinedWorkspaces.some((item) => item.id === matchedWorkspace.id);
    if (isMember) {
      selectWorkspace(matchedWorkspace);
      return;
    }

    setActiveJoinWorkspaceId(matchedWorkspace.id);
  };

  const leaveWorkspace = async (workspace: Workspace) => {
    setError(null);

    try {
      await api.delete(`/workspaces/${workspace.id}/leave`);
      const updatedWorkspaces = joinedWorkspaces.filter((item) => item.id !== workspace.id);
      setJoinedWorkspaces(updatedWorkspaces);
      setStoreWorkspaces(updatedWorkspaces);
      setDiscoverableWorkspaces(
        discoverableWorkspaces.map((item) =>
          item.id === workspace.id ? { ...item, is_member: false } : item
        )
      );

      if (currentWorkspace?.id === workspace.id) {
        setCurrentWorkspace(updatedWorkspaces[0] ?? null);
      }
    } catch (leaveError) {
      console.error("Failed to leave workspace:", leaveError);
      const apiError = leaveError as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || text.leaveError);
    }
  };

  const joinWorkspace = async (workspace: Workspace) => {
    setError(null);

    const normalizedPassword = joinPassword.trim();
    if (!normalizedPassword) {
      setError(text.enterPassword);
      return;
    }

    try {
      await api.post<WorkspaceMember>(`/workspaces/${workspace.id}/join`, {
        password: normalizedPassword,
      });

      const joinedWorkspace = { ...workspace, is_member: true };
      await loadWorkspaces();
      setCurrentWorkspace(joinedWorkspace);
      setJoinPassword("");
      setActiveJoinWorkspaceId(null);
      router.push("/dashboard");
    } catch (joinError) {
      console.error("Failed to join workspace:", joinError);
      const apiError = joinError as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || text.joinError);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredJoinedWorkspaces = joinedWorkspaces.filter((workspace) =>
    workspace.name.toLowerCase().includes(normalizedSearch)
  );
  const filteredDiscoverableWorkspaces = discoverableWorkspaces.filter((workspace) =>
    workspace.name.toLowerCase().includes(normalizedSearch)
  );

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-8 sm:py-10">
      <div className="w-full max-w-4xl space-y-6">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">{text.choose}</h2>
          <p className="mt-2 text-gray-600">
            {isAdmin ? text.adminHint : text.salesHint}
          </p>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!isAdmin && (
          <form onSubmit={openWorkspaceByName} className="rounded-2xl border border-gray-100 bg-white p-4 shadow-xl">
            <label className="mb-2 block text-sm font-medium text-gray-700">{text.findByName}</label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder={text.startTyping}
                className="w-full rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
              >
                {text.find}
              </button>
            </div>
          </form>
        )}

        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-xl">
            <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-xl font-semibold text-gray-900">{text.yourWorkspaces}</h3>
                <p className="mt-1 text-sm text-gray-500">
                  {joinedWorkspaces.length > 0
                    ? text.openMember
                    : text.noneJoined}
                </p>
              </div>
            </div>

            {filteredJoinedWorkspaces.length > 0 ? (
              <div className="space-y-3">
                {filteredJoinedWorkspaces.map((workspace) => (
                  <div
                    key={workspace.id}
                    className={`rounded-xl border-2 p-4 transition ${
                      currentWorkspace?.id === workspace.id
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200"
                    }`}
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <button onClick={() => selectWorkspace(workspace)} className="flex-1 text-left">
                        <div className="font-medium text-gray-900">{workspace.name}</div>
                        {workspace.description && (
                          <div className="mt-1 text-sm text-gray-500">{workspace.description}</div>
                        )}
                      </button>
                      <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                        {text.member}
                      </span>
                    </div>
                    {!isAdmin && (
                      <button
                        onClick={() => leaveWorkspace(workspace)}
                        className="mt-4 rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50"
                      >
                         {text.leave}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-gray-200 px-4 py-8 text-center text-gray-500">
                {isAdmin
                  ? text.createFirstAdmin
                  : text.createFirstSales}
              </div>
            )}
          </div>

          <div className="space-y-6">
            {isAdmin ? (
              <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-xl">
                <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">{text.createWorkspace}</h3>
                    <p className="mt-1 text-sm text-gray-500">{text.createWorkspaceHint}</p>
                  </div>
                  {!showCreate && (
                    <button
                      onClick={() => setShowCreate(true)}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition"
                    >
                       {text.newWorkspace}
                    </button>
                  )}
                </div>

                {showCreate ? (
                  <form onSubmit={createWorkspace} className="space-y-4">
                    <input
                      type="text"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder={text.workspaceName}
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500"
                      required
                    />
                    <textarea
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                      placeholder={text.descriptionOptional}
                      rows={3}
                      className="w-full resize-none rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder={text.workspacePassword}
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500"
                      required
                    />
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <button
                        type="submit"
                        className="flex-1 rounded-lg bg-blue-600 py-2 text-white font-medium hover:bg-blue-700 transition"
                      >
                         {text.create}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowCreate(false);
                          setNewName("");
                          setNewDescription("");
                          setNewPassword("");
                          setError(null);
                        }}
                        className="flex-1 rounded-lg border border-gray-300 py-2 font-medium hover:bg-gray-50 transition"
                      >
                         {text.cancel}
                      </button>
                    </div>
                  </form>
                ) : null}
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-xl">
                 <h3 className="text-xl font-semibold text-gray-900">{text.available}</h3>
                 <p className="mt-1 text-sm text-gray-500">{text.availableHint}</p>

                <div className="mt-4 space-y-3">
                  {filteredDiscoverableWorkspaces.length > 0 ? (
                    filteredDiscoverableWorkspaces.map((workspace) => {
                      const isMember = workspace.is_member || joinedWorkspaces.some((item) => item.id === workspace.id);

                      return (
                        <div key={workspace.id} className="rounded-xl border border-gray-200 p-4">
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <div className="font-medium text-gray-900">{workspace.name}</div>
                              {workspace.description && (
                                <div className="mt-1 text-sm text-gray-500">{workspace.description}</div>
                              )}
                            </div>
                            <span className={`rounded-full px-3 py-1 text-xs font-medium ${isMember ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                              {isMember ? text.joined : text.passwordRequired}
                            </span>
                          </div>

                          <div className="mt-4">
                            {isMember ? (
                              <button
                                onClick={() => selectWorkspace(workspace)}
                                className="w-full rounded-lg bg-blue-600 py-2 text-white font-medium hover:bg-blue-700 transition"
                              >
                                 {text.openWorkspace}
                              </button>
                            ) : activeJoinWorkspaceId === workspace.id ? (
                              <form
                                className="space-y-3"
                                onSubmit={(e) => {
                                  e.preventDefault();
                                  joinWorkspace(workspace);
                                }}
                              >
                                <input
                                  type="password"
                                  value={joinPassword}
                                  onChange={(e) => setJoinPassword(e.target.value)}
                                   placeholder={text.enterWorkspacePasswordShort}
                                  className="w-full rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500"
                                  autoFocus
                                />
                                <div className="flex flex-col gap-3 sm:flex-row">
                                  <button
                                    type="submit"
                                    className="flex-1 rounded-lg bg-blue-600 py-2 text-white font-medium hover:bg-blue-700 transition"
                                  >
                                     {text.joinWorkspace}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setActiveJoinWorkspaceId(null);
                                      setJoinPassword("");
                                      setError(null);
                                    }}
                                    className="flex-1 rounded-lg border border-gray-300 py-2 font-medium hover:bg-gray-50 transition"
                                  >
                                     {text.cancel}
                                  </button>
                                </div>
                              </form>
                            ) : (
                              <button
                                onClick={() => {
                                  setActiveJoinWorkspaceId(workspace.id);
                                  setJoinPassword("");
                                  setError(null);
                                }}
                                className="w-full rounded-lg border border-blue-200 bg-blue-50 py-2 text-blue-700 font-medium hover:bg-blue-100 transition"
                              >
                                 {text.enterPasswordButton}
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="rounded-xl border border-dashed border-gray-200 px-4 py-8 text-center text-gray-500">
                       {text.noWorkspaces}
                     </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
