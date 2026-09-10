import { apiFetch } from "@/api/client";

export interface ProviderConnection {
  id: number;
  display_name: string;
  provider_type: string;
  base_url: string;
  model: string;
  enabled: boolean;
  api_key_configured: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderConnectionInput {
  display_name: string;
  provider_type: string;
  base_url: string;
  api_key?: string;
  model: string;
  enabled?: boolean;
}

const endpoint = "/api/provider-connections";

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? `Provider request failed: ${res.status}`);
  }
  return res.status === 204 ? (undefined as T) : (await res.json() as T);
}

export async function fetchProviderConnections(): Promise<{ connections: ProviderConnection[] }> {
  return parse(await apiFetch(endpoint));
}

export async function createProviderConnection(data: ProviderConnectionInput) {
  return parse<ProviderConnection>(await apiFetch(endpoint, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  }));
}

export async function updateProviderConnection(id: number, data: Partial<ProviderConnectionInput>) {
  return parse<ProviderConnection>(await apiFetch(`${endpoint}/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  }));
}

export async function deleteProviderConnection(id: number) {
  return parse<void>(await apiFetch(`${endpoint}/${id}`, { method: "DELETE" }));
}

export async function testProviderConnection(id: number) {
  return parse<{ success: boolean; message: string; models: string[] }>(await apiFetch(`${endpoint}/${id}/test`, { method: "POST" }));
}

export async function discoverProviderModels(id: number) {
  return parse<{ models: string[] }>(await apiFetch(`${endpoint}/${id}/models`));
}
