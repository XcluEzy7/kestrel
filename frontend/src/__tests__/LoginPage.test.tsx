/** Shoo callback must establish Kestrel session before redirecting. */

import { screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "@/pages/LoginPage";
import { renderWithProviders } from "@/test-utils";

const { mockAuthClient, mockLoginWithShoo } = vi.hoisted(() => ({
  mockAuthClient: {
    parseCallback: vi.fn(),
    finishSignIn: vi.fn(),
  },
  mockLoginWithShoo: vi.fn(),
}));

vi.mock("@shoojs/react", () => {
  return {
    useShooAuth: () => {
      const [identity, setIdentity] = useState(() => {
        const raw = localStorage.getItem("shoo_identity");
        const stored = raw ? JSON.parse(raw) as { userId?: string; token?: string } : {};
        return { userId: stored.userId ?? null, token: stored.token };
      });
      return {
        identity,
        loading: false,
        error: null,
        signIn: vi.fn(),
        clearIdentity: () => {
          localStorage.removeItem("shoo_identity");
          setIdentity({ userId: null });
        },
        refreshIdentity: () => {
          const raw = localStorage.getItem("shoo_identity");
          const stored = raw ? JSON.parse(raw) as { userId?: string; token?: string } : {};
          setIdentity({ userId: stored.userId ?? null, token: stored.token });
        },
        claims: null,
        sessionState: "unknown",
        authClient: mockAuthClient,
      };
    },
  };
});

vi.mock("@/api/auth", () => ({ loginWithShoo: mockLoginWithShoo }));

describe("LoginPage", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/auth/callback?code=code&state=state");
    localStorage.clear();
    localStorage.setItem("shoo_identity", JSON.stringify({ userId: "old-user", token: "stale-token" }));
    sessionStorage.clear();
    sessionStorage.setItem("kestrel_auth_return_to", "/settings");
    mockAuthClient.parseCallback.mockImplementation(() => (
      window.location.search ? { code: "code", state: "state" } : null
    ));
    mockAuthClient.finishSignIn.mockImplementation(async () => {
      localStorage.setItem("shoo_identity", JSON.stringify({ userId: "user-1", token: "id-token" }));
      window.history.replaceState({}, "", "/auth/callback");
      return { pairwise_sub: "user-1", id_token: "id-token" };
    });
    mockLoginWithShoo.mockResolvedValue({ authenticated: true, profile_id: 1 });
  });

  it("verifies callback token with Kestrel before returning to the app", async () => {
    renderWithProviders(
      <Routes>
        <Route path="/auth/callback" element={<LoginPage />} />
        <Route path="/settings" element={<div>Settings</div>} />
      </Routes>,
      { route: "/auth/callback" },
    );

    await waitFor(() => expect(mockAuthClient.finishSignIn).toHaveBeenCalledWith({
      redirectAfter: false,
      consumeReturnTo: false,
    }));
    await waitFor(() => expect(mockLoginWithShoo).toHaveBeenCalledWith("id-token"));
    expect(mockLoginWithShoo).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Settings")).toBeInTheDocument();
    expect(sessionStorage.getItem("kestrel_auth_return_to")).toBeNull();
  });
});
