/**
 * SettingsPage — Settings page with tabbed sections for Profiles and Integrations.
 *
 * Supports:
 * - VAL-PIPE-017 (profile create/edit flow)
 * - VAL-PUSH-006 (all integrations have settings section with credential fields,
 *                  on/off toggle, status indicator)
 */

import { useState, useCallback } from "react";
import {
  useProfiles,
  useCreateProfile,
  useUpdateProfile,
  useDeleteProfile,
} from "@/hooks/useProfiles";
import type { ProfileResponse, ProfileCreate } from "@/api/profiles";
import {
  fetchIntegrations,
  updateIntegration,
  testIntegration,
} from "@/api/integrations";
import type {
  IntegrationConfigResponse,
  IntegrationConfigUpdate,
} from "@/api/integrations";
import {
  createMcpToken,
  fetchMcpTokens,
  revokeMcpToken,
} from "@/api/auth";
import type {
  McpTokenCreate,
  McpTokenCreatedResponse,
  McpTokenResponse,
} from "@/api/auth";
import { IntegrationPanel } from "@/components/IntegrationPanel";
import { ProviderConnections } from "@/components/ProviderConnections";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  User,
  Plus,
  Pencil,
  Trash2,
  Save,
  X,
  Plug,
  Copy,
} from "lucide-react";

type SettingsTab = "profiles" | "integrations";

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("integrations");

  return (
    <section data-testid="settings-page" className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8" aria-label="Settings tabs">
          <button
            data-testid="tab-integrations"
            onClick={() => setActiveTab("integrations")}
            className={`whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === "integrations"
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
            }`}
          >
            <Plug className="mr-2 inline-block h-4 w-4" />
            Integrations
          </button>
          <button
            data-testid="tab-profiles"
            onClick={() => setActiveTab("profiles")}
            className={`whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === "profiles"
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
            }`}
          >
            <User className="mr-2 inline-block h-4 w-4" />
            Profiles
          </button>
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === "integrations" && <IntegrationsSection />}
      {activeTab === "profiles" && <ProfilesSection />}
    </section>
  );
}

// ========================= Integrations Section =========================

function IntegrationsSection() {
  const queryClient = useQueryClient();

  const {
    data,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["integrations"],
    queryFn: fetchIntegrations,
  });

  const [savingName, setSavingName] = useState<string | null>(null);
  const [testingName, setTestingName] = useState<string | null>(null);

  const updateMutation = useMutation({
    mutationFn: ({
      name,
      payload,
    }: {
      name: string;
      payload: IntegrationConfigUpdate;
    }) => updateIntegration(name, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
    },
    onSettled: () => {
      setSavingName(null);
    },
  });

  const handleUpdate = useCallback(
    async (name: string, payload: IntegrationConfigUpdate) => {
      setSavingName(name);
      await updateMutation.mutateAsync({ name, payload });
    },
    [updateMutation],
  );

  const handleTest = useCallback(
    async (
      name: string,
    ): Promise<{ success: boolean; message: string }> => {
      setTestingName(name);
      try {
        const result = await testIntegration(name);
        await queryClient.invalidateQueries({ queryKey: ["integrations"] });
        return { success: result.success, message: result.message };
      } catch (e) {
        return {
          success: false,
          message: e instanceof Error ? e.message : "Test failed",
        };
      } finally {
        setTestingName(null);
      }
    },
    [queryClient],
  );

  if (isLoading) {
    return (
      <div
        data-testid="integrations-loading"
        className="flex items-center justify-center py-20"
      >
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-gray-900" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        data-testid="integrations-error"
        className="py-20 text-center"
      >
        <p className="text-lg font-medium text-red-700">
          {error instanceof Error ? error.message : String(error)}
        </p>
      </div>
    );
  }

  const integrations = data?.integrations ?? [];

  return (
    <div data-testid="integrations-section" className="space-y-4">
      <p className="text-sm text-gray-500">
        Configure external integrations. Enable an integration, enter your
        credentials, and test the connection.
      </p>
      <ProviderConnections />
      <McpTokensSection />
      {integrations.map((integration: IntegrationConfigResponse) => (
        <IntegrationPanel
          key={integration.name}
          integration={integration}
          onUpdate={handleUpdate}
          onTest={handleTest}
          isSaving={savingName === integration.name}
          isTesting={testingName === integration.name}
        />
      ))}
    </div>
  );
}

// ========================= MCP Tokens Section =========================

function McpTokensSection() {
  const queryClient = useQueryClient();
  const { data: tokens, isLoading, error } = useQuery({
    queryKey: ["mcp-tokens"],
    queryFn: fetchMcpTokens,
  });
  const [name, setName] = useState("MCP client");
  const [readScope, setReadScope] = useState(true);
  const [writeScope, setWriteScope] = useState(false);
  const [expiresInDays, setExpiresInDays] = useState("");
  const [createdToken, setCreatedToken] = useState<McpTokenCreatedResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const createMutation = useMutation({
    mutationFn: (payload: McpTokenCreate) => createMcpToken(payload),
    onSuccess: (token) => {
      setCreatedToken(token);
      setCopied(false);
      setName("MCP client");
      setReadScope(true);
      setWriteScope(false);
      setExpiresInDays("");
      void queryClient.invalidateQueries({ queryKey: ["mcp-tokens"] });
    },
  });
  const revokeMutation = useMutation({
    mutationFn: revokeMcpToken,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mcp-tokens"] });
    },
  });

  const handleCreate = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const scopes = [
      ...(readScope ? ["mcp:read"] : []),
      ...(writeScope ? ["mcp:write"] : []),
    ];
    if (!name.trim() || scopes.length === 0) return;
    createMutation.mutate({
      name: name.trim(),
      scopes,
      expires_in_days: expiresInDays ? Number(expiresInDays) : null,
    });
  };

  const handleRevoke = (token: McpTokenResponse) => {
    if (token.revoked_at || !window.confirm(`Revoke MCP token “${token.name}”?`)) return;
    revokeMutation.mutate(token.id);
  };

  const handleCopy = async () => {
    if (!createdToken) return;
    try {
      await navigator.clipboard.writeText(createdToken.token);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section
      data-testid="mcp-tokens-section"
      aria-labelledby="mcp-tokens-heading"
      className="rounded-lg border bg-white p-6 shadow-sm"
    >
      <div className="mb-4">
        <h2 id="mcp-tokens-heading" className="text-lg font-semibold text-gray-900">
          MCP server tokens
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Create scoped tokens for remote MCP clients. Secrets appear once and are never stored in this list.
        </p>
      </div>

      {isLoading && (
        <p data-testid="mcp-tokens-loading" className="text-sm text-gray-500">Loading MCP tokens…</p>
      )}
      {error && (
        <p data-testid="mcp-tokens-error" role="alert" className="mb-4 text-sm text-red-700">
          {error instanceof Error ? error.message : String(error)}
        </p>
      )}
      {(createMutation.isError || revokeMutation.isError) && (
        <p data-testid="mcp-tokens-mutation-error" role="alert" className="mb-4 text-sm text-red-700">
          {(createMutation.error ?? revokeMutation.error) instanceof Error
            ? (createMutation.error ?? revokeMutation.error)?.message
            : "MCP token request failed"}
        </p>
      )}

      {createdToken && (
        <div data-testid="mcp-token-secret" role="status" className="mb-6 rounded-md border border-amber-300 bg-amber-50 p-4">
          <p className="font-medium text-amber-900">Copy this secret now. It will not be shown again.</p>
          <div className="mt-2 flex items-center gap-2">
            <code className="min-w-0 flex-1 break-all rounded bg-white px-2 py-1 text-sm text-gray-900">
              {createdToken.token}
            </code>
            <button
              type="button"
              onClick={handleCopy}
              aria-label="Copy MCP token secret"
              className="inline-flex shrink-0 items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-gray-700 hover:bg-gray-50"
            >
              <Copy className="h-4 w-4" />
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      {!isLoading && !error && (
        <div className="mb-6 overflow-x-auto">
          <h3 className="mb-2 text-sm font-medium text-gray-900">Existing tokens</h3>
          {(tokens ?? []).length === 0 ? (
            <p data-testid="mcp-tokens-empty" className="text-sm text-gray-500">No MCP tokens created.</p>
          ) : (
            <ul data-testid="mcp-tokens-list" className="divide-y rounded-md border">
              {(tokens ?? []).map((token) => (
                <li key={token.id} className="flex items-center justify-between gap-4 p-3 text-sm">
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900">{token.name}</p>
                    <p className="text-gray-500">
                      {token.token_prefix} · {token.scopes.join(", ")}
                      {token.expires_at ? ` · Expires ${new Date(token.expires_at).toLocaleDateString()}` : " · Never expires"}
                      {token.revoked_at ? " · Revoked" : ""}
                    </p>
                  </div>
                  {!token.revoked_at && (
                    <button
                      type="button"
                      onClick={() => handleRevoke(token)}
                      disabled={revokeMutation.isPending}
                      className="shrink-0 rounded-md border border-red-300 px-2 py-1 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
                    >
                      Revoke
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <form onSubmit={handleCreate} className="space-y-4 border-t pt-4">
        <h3 className="text-sm font-medium text-gray-900">Create token</h3>
        <div>
          <label htmlFor="mcp-token-name" className="block text-sm font-medium text-gray-700">Name</label>
          <input
            id="mcp-token-name"
            data-testid="mcp-token-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={100}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
          />
        </div>
        <fieldset>
          <legend className="text-sm font-medium text-gray-700">Scopes</legend>
          <div className="mt-2 flex flex-wrap gap-4">
            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={readScope} onChange={(event) => setReadScope(event.target.checked)} />
              Read
            </label>
            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={writeScope} onChange={(event) => setWriteScope(event.target.checked)} />
              Write
            </label>
          </div>
        </fieldset>
        <div>
          <label htmlFor="mcp-token-expiry" className="block text-sm font-medium text-gray-700">Expires in</label>
          <select
            id="mcp-token-expiry"
            data-testid="mcp-token-expiry"
            value={expiresInDays}
            onChange={(event) => setExpiresInDays(event.target.value)}
            className="mt-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
          >
            <option value="">Never</option>
            <option value="7">7 days</option>
            <option value="30">30 days</option>
            <option value="90">90 days</option>
            <option value="365">365 days</option>
          </select>
        </div>
        <button
          type="submit"
          data-testid="mcp-token-create"
          disabled={createMutation.isPending || !name.trim() || (!readScope && !writeScope)}
          className="inline-flex items-center rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-800 disabled:opacity-50"
        >
          {createMutation.isPending ? "Creating…" : "Create token"}
        </button>
      </form>
    </section>
  );
}

// ========================= Profiles Section =========================

function ProfilesSection() {
  const { data, isLoading, error } = useProfiles();
  const createMutation = useCreateProfile();
  const updateMutation = useUpdateProfile();
  const deleteMutation = useDeleteProfile();

  const [editingId, setEditingId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [formData, setFormData] = useState<ProfileCreate>({
    name: "",
    email: "",
    location: "",
    job_family: "",
  });

  const handleStartEdit = useCallback((profile: ProfileResponse) => {
    setEditingId(profile.id);
    setIsCreating(false);
    setFormData({
      name: profile.name,
      email: profile.email ?? "",
      location: profile.location ?? "",
      job_family: profile.job_family ?? "",
    });
  }, []);

  const handleStartCreate = useCallback(() => {
    setEditingId(null);
    setIsCreating(true);
    setFormData({ name: "", email: "", location: "", job_family: "" });
  }, []);

  const handleCancel = useCallback(() => {
    setEditingId(null);
    setIsCreating(false);
    setFormData({ name: "", email: "", location: "", job_family: "" });
  }, []);

  const handleSave = useCallback(() => {
    if (isCreating) {
      createMutation.mutate(formData, {
        onSuccess: () => {
          setIsCreating(false);
          setFormData({ name: "", email: "", location: "", job_family: "" });
        },
      });
    } else if (editingId !== null) {
      updateMutation.mutate(
        { id: editingId, data: formData },
        {
          onSuccess: () => {
            setEditingId(null);
            setFormData({ name: "", email: "", location: "", job_family: "" });
          },
        },
      );
    }
  }, [isCreating, editingId, formData, createMutation, updateMutation]);

  const handleDelete = useCallback(
    (id: number) => {
      deleteMutation.mutate(id);
    },
    [deleteMutation],
  );

  const handleFieldChange = useCallback(
    (field: keyof ProfileCreate, value: string) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  if (isLoading) {
    return (
      <div
        data-testid="settings-loading"
        className="flex items-center justify-center py-20"
      >
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-gray-900" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        data-testid="settings-error"
        className="py-20 text-center"
      >
        <p className="text-lg font-medium text-red-700">
          {error instanceof Error ? error.message : String(error)}
        </p>
      </div>
    );
  }

  const profiles = data?.profiles ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Manage your user profiles for the career platform.
        </p>
        {!isCreating && editingId === null && (
          <button
            data-testid="create-profile-button"
            onClick={handleStartCreate}
            className="inline-flex items-center gap-1 rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-800"
          >
            <Plus className="h-4 w-4" />
            New Profile
          </button>
        )}
      </div>

      {/* Mutation errors */}
      {(createMutation.isError ||
        updateMutation.isError ||
        deleteMutation.isError) && (
        <div
          data-testid="settings-mutation-error"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700"
        >
          {(() => {
            const err = createMutation.error ?? updateMutation.error ?? deleteMutation.error;
            return err instanceof Error ? err.message : "An error occurred";
          })()}
        </div>
      )}

      {/* Create form */}
      {isCreating && (
        <div
          data-testid="profile-create-form"
          className="rounded-lg border bg-white p-6 shadow-sm"
        >
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            Create New Profile
          </h2>
          <ProfileForm
            formData={formData}
            onChange={handleFieldChange}
            onSave={handleSave}
            onCancel={handleCancel}
            isSaving={createMutation.isPending}
            testIdPrefix="create"
          />
        </div>
      )}

      {/* Profiles list */}
      <div className="space-y-4">
        {profiles.length === 0 && !isCreating ? (
          <div
            data-testid="no-profiles"
            className="rounded-lg border border-dashed border-gray-300 p-8 text-center"
          >
            <User className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-2 text-sm text-gray-500">
              No profiles yet. Create one to get started.
            </p>
            <button
              data-testid="create-profile-cta"
              onClick={handleStartCreate}
              className="mt-4 inline-flex items-center gap-1 rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-800"
            >
              <Plus className="h-4 w-4" />
              Create Profile
            </button>
          </div>
        ) : (
          profiles.map((profile) => (
            <div
              key={profile.id}
              data-testid={`profile-card-${profile.id}`}
              className="rounded-lg border bg-white p-6 shadow-sm"
            >
              {editingId === profile.id ? (
                <div data-testid={`profile-edit-form-${profile.id}`}>
                  <h3 className="mb-4 text-lg font-semibold text-gray-900">
                    Edit Profile
                  </h3>
                  <ProfileForm
                    formData={formData}
                    onChange={handleFieldChange}
                    onSave={handleSave}
                    onCancel={handleCancel}
                    isSaving={updateMutation.isPending}
                    testIdPrefix={`edit-${profile.id}`}
                  />
                </div>
              ) : (
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <User className="h-5 w-5 text-gray-400" />
                      <h3
                        data-testid={`profile-name-${profile.id}`}
                        className="text-lg font-medium text-gray-900"
                      >
                        {profile.name}
                      </h3>
                    </div>
                    <div className="mt-2 space-y-1 text-sm text-gray-600">
                      {profile.email && (
                        <p data-testid={`profile-email-${profile.id}`}>
                          📧 {profile.email}
                        </p>
                      )}
                      {profile.location && (
                        <p data-testid={`profile-location-${profile.id}`}>
                          📍 {profile.location}
                        </p>
                      )}
                      {profile.job_family && (
                        <p data-testid={`profile-job-family-${profile.id}`}>
                          💼 {profile.job_family}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      data-testid={`edit-profile-${profile.id}`}
                      onClick={() => handleStartEdit(profile)}
                      className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <Pencil className="h-3 w-3" />
                      Edit
                    </button>
                    <button
                      data-testid={`delete-profile-${profile.id}`}
                      onClick={() => handleDelete(profile.id)}
                      disabled={deleteMutation.isPending}
                      className="inline-flex items-center gap-1 rounded-md border border-red-300 bg-white px-2 py-1 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ---- Profile Form Component ----

function ProfileForm({
  formData,
  onChange,
  onSave,
  onCancel,
  isSaving,
  testIdPrefix,
}: Readonly<{
  formData: ProfileCreate;
  onChange: (field: keyof ProfileCreate, value: string) => void;
  onSave: () => void;
  onCancel: () => void;
  isSaving: boolean;
  testIdPrefix: string;
}>) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={`${testIdPrefix}-name-input`} className="block text-sm font-medium text-gray-700">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            id={`${testIdPrefix}-name-input`}
            data-testid={`${testIdPrefix}-name-input`}
            type="text"
            value={formData.name}
            onChange={(e) => onChange("name", e.target.value)}
            placeholder="Full name"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
          />
        </div>
        <div>
          <label htmlFor={`${testIdPrefix}-email-input`} className="block text-sm font-medium text-gray-700">
            Email
          </label>
          <input
            id={`${testIdPrefix}-email-input`}
            data-testid={`${testIdPrefix}-email-input`}
            type="email"
            value={formData.email ?? ""}
            onChange={(e) => onChange("email", e.target.value)}
            placeholder="email@example.com"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
          />
        </div>
        <div>
          <label htmlFor={`${testIdPrefix}-location-input`} className="block text-sm font-medium text-gray-700">
            Location
          </label>
          <input
            id={`${testIdPrefix}-location-input`}
            data-testid={`${testIdPrefix}-location-input`}
            type="text"
            value={formData.location ?? ""}
            onChange={(e) => onChange("location", e.target.value)}
            placeholder="City, Country"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
          />
        </div>
        <div>
          <label htmlFor={`${testIdPrefix}-job-family-input`} className="block text-sm font-medium text-gray-700">
            Job Family
          </label>
          <input
            id={`${testIdPrefix}-job-family-input`}
            data-testid={`${testIdPrefix}-job-family-input`}
            type="text"
            value={formData.job_family ?? ""}
            onChange={(e) => onChange("job_family", e.target.value)}
            placeholder="e.g., Senior TPM / Product Engineer"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
          />
        </div>
      </div>
      <div className="flex items-center gap-2 pt-2">
        <button
          data-testid={`${testIdPrefix}-save-button`}
          onClick={onSave}
          disabled={isSaving || !formData.name.trim()}
          className="inline-flex items-center gap-1 rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-800 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {isSaving ? "Saving…" : "Save"}
        </button>
        <button
          data-testid={`${testIdPrefix}-cancel-button`}
          onClick={onCancel}
          className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
        >
          <X className="h-4 w-4" />
          Cancel
        </button>
      </div>
    </div>
  );
}
