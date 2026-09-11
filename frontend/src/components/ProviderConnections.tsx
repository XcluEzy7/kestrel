import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createProviderConnection, deleteProviderConnection, discoverDraftProviderModels, discoverProviderModels,
  fetchProviderConnections, testProviderConnection, updateProviderConnection,
  type ProviderConnection, type ProviderConnectionInput,
} from "@/api/providerConnections";

const blank: ProviderConnectionInput = {
  display_name: "", provider_type: "openai_compatible", base_url: "https://api.openai.com/v1", model: "", enabled: true,
};

export function ProviderConnections() {
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["provider-connections"], queryFn: fetchProviderConnections });
  const [draft, setDraft] = useState<ProviderConnectionInput>(blank);
  const [editing, setEditing] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
  const save = useMutation({ mutationFn: () => editing == null ? createProviderConnection(draft) : updateProviderConnection(editing, draft), onSuccess: () => { setDraft(blank); setEditing(null); qc.invalidateQueries({ queryKey: ["provider-connections"] }); } });
  const remove = useMutation({ mutationFn: deleteProviderConnection, onSuccess: () => qc.invalidateQueries({ queryKey: ["provider-connections"] }) });
  const test = useMutation({ mutationFn: testProviderConnection, onSuccess: (result) => setMessage(result.success ? `Connected. Models: ${result.models.join(", ") || "none reported"}` : result.message) });
  const models = useMutation({ mutationFn: () => editing != null ? discoverProviderModels(editing) : discoverDraftProviderModels({ provider_type: draft.provider_type, base_url: draft.base_url, api_key: draft.api_key }), onSuccess: (result) => { setDiscoveredModels(result.models); setDraft((current) => ({ ...current, model: current.model || result.models[0] || "" })); setMessage(result.models.length ? `Models found: ${result.models.join(", ")}` : "Provider reported no models."); }, onError: (error: Error) => setMessage(error.message) });

  if (query.isLoading) return <p data-testid="provider-connections-loading">Loading providers…</p>;
  if (query.isError) return <p className="text-red-700">{query.error.message}</p>;
  const connections = query.data?.connections ?? [];
  const set = (key: keyof ProviderConnectionInput, value: string | boolean) => setDraft((current) => ({ ...current, [key]: value }));
  const edit = (connection: ProviderConnection) => { setEditing(connection.id); setDraft({ display_name: connection.display_name, provider_type: connection.provider_type, base_url: connection.base_url, model: connection.model ?? "", enabled: connection.enabled }); setDiscoveredModels([]); setMessage(null); };
  const toggle = (connection: ProviderConnection) => updateProviderConnection(connection.id, { enabled: !connection.enabled }).then(() => qc.invalidateQueries({ queryKey: ["provider-connections"] }));

  return <div data-testid="provider-connections" className="space-y-4 rounded-lg border bg-white p-6">
    <div><h2 className="text-lg font-semibold">AI provider connections</h2><p className="text-sm text-gray-500">Use OpenAI-compatible providers, Ollama Cloud, or local Ollama. API keys stay encrypted and are never displayed.</p></div>
    {connections.map((connection) => <div key={connection.id} className="flex items-center justify-between rounded border p-3" data-testid={`provider-connection-${connection.id}`}>
      <div><strong>{connection.display_name}</strong><p className="text-sm text-gray-500">{connection.provider_type} · {connection.base_url} · {connection.model}</p><p className="text-xs">{connection.enabled ? "Enabled" : "Disabled"} · API key {connection.api_key_configured ? "configured" : "not configured"}</p></div>
      <div className="flex gap-2"><button type="button" className="rounded border px-2 py-1 text-sm" onClick={() => edit(connection)}>Edit</button><button type="button" className="rounded border px-2 py-1 text-sm" onClick={() => test.mutate(connection.id)}>Test</button><button type="button" className="rounded border px-2 py-1 text-sm" onClick={() => toggle(connection)}>{connection.enabled ? "Disable" : "Enable"}</button><button type="button" className="rounded border border-red-300 px-2 py-1 text-sm text-red-700" onClick={() => remove.mutate(connection.id)}>Delete</button></div>
    </div>)}
    <form className="grid gap-3 md:grid-cols-2" onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
      <label>Display name<input required value={draft.display_name} onChange={(e) => set("display_name", e.target.value)} /></label>
      <label>Provider type<select value={draft.provider_type} onChange={(e) => set("provider_type", e.target.value)}><option value="openai_compatible">OpenAI-compatible</option><option value="ollama_cloud">Ollama Cloud</option><option value="ollama_local">Local Ollama</option></select></label>
      <label>Base URL<input required type="url" value={draft.base_url} onChange={(e) => set("base_url", e.target.value)} placeholder="https://ollama.com/v1" /></label>
      <label>Bearer API key<input type="password" value={draft.api_key ?? ""} onChange={(e) => set("api_key", e.target.value)} placeholder="Leave blank to keep current" /></label>
      <label>Model<input value={draft.model ?? ""} onChange={(e) => set("model", e.target.value)} placeholder="Discover or enter model override" />{discoveredModels.length > 0 && <select aria-label="Discovered models" value={draft.model ?? ""} onChange={(e) => set("model", e.target.value)}><option value="">Select discovered model</option>{discoveredModels.map((model) => <option key={model} value={model}>{model}</option>)}</select>}<button type="button" onClick={() => models.mutate()}>Discover models</button></label>
      <label className="flex items-center gap-2"><input type="checkbox" checked={draft.enabled !== false} onChange={(e) => set("enabled", e.target.checked)} /> Enabled</label>
      <div className="md:col-span-2 flex gap-2"><button className="rounded bg-gray-900 px-3 py-2 text-white" type="submit">{editing == null ? "Add connection" : "Save connection"}</button>{editing != null && <button type="button" className="rounded border px-3 py-2" onClick={() => { setEditing(null); setDraft(blank); }}>Cancel</button>}</div>
    </form>
    {message && <p role="status">{message}</p>}
  </div>;
}
