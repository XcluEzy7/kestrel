/** Browser session API for Shoo authentication. */

import { apiFetch } from "./client";

export type AuthState =
  | { authenticated: false; auth_required?: boolean; debug_auth_enabled?: boolean }
  | { authenticated: true; profile_id: number; auth_required?: boolean; debug_auth_enabled?: boolean };

export interface McpTokenResponse {
  id: number;
  name: string;
  token_prefix: string;
  scopes: string[];
  profile_id: number;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface McpTokenCreatedResponse extends McpTokenResponse {
  token: string;
}

export interface McpTokenCreate {
  name: string;
  scopes: string[];
  expires_in_days: number | null;
}

export async function fetchAuthState(): Promise<AuthState> {
  const response = await apiFetch("/api/auth/shoo/me");
  if (!response.ok) throw new Error(`Failed to check authentication: ${response.status}`);
  return response.json() as Promise<AuthState>;
}

export async function loginWithShoo(idToken: string): Promise<AuthState> {
  const response = await apiFetch("/api/auth/shoo/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });
  if (!response.ok) throw new Error("Shoo sign-in failed");
  return response.json() as Promise<AuthState>;
}

export async function loginWithDebug(secret: string): Promise<AuthState> {
  const response = await apiFetch("/api/auth/debug", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ secret }),
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body !== null && typeof body === "object" && "detail" in body &&
      typeof body.detail === "string" ? body.detail : undefined;
    throw new Error(detail ?? "Debug sign-in failed");
  }
  return response.json() as Promise<AuthState>;
}

export async function logout(): Promise<void> {
  const response = await apiFetch("/api/auth/shoo/logout", { method: "POST" });
  if (!response.ok) throw new Error("Sign-out failed");
}

/** List account-owned MCP tokens without returning their secrets. */
export async function fetchMcpTokens(): Promise<McpTokenResponse[]> {
  const response = await apiFetch("/api/auth/shoo/mcp-tokens");
  if (!response.ok) {
    throw new Error(`Failed to fetch MCP tokens: ${response.status}`);
  }
  return response.json() as Promise<McpTokenResponse[]>;
}

/** Create one account-owned MCP token. The secret is returned only once. */
export async function createMcpToken(
  data: McpTokenCreate,
): Promise<McpTokenCreatedResponse> {
  const response = await apiFetch("/api/auth/shoo/mcp-tokens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ??
        `Failed to create MCP token: ${response.status}`,
    );
  }
  return response.json() as Promise<McpTokenCreatedResponse>;
}

/** Revoke one account-owned MCP token. */
export async function revokeMcpToken(tokenId: number): Promise<void> {
  const response = await apiFetch(`/api/auth/shoo/mcp-tokens/${tokenId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ??
        `Failed to revoke MCP token: ${response.status}`,
    );
  }
}
