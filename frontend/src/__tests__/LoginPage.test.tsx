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

vi.mock("@shoojs/react", async () => {
  return {
    useShooAuth: () => {
      const [identity, setIdentity] = useState<{ userId: string | null; token?: string }>({
        userId: null,
      });
      return {
        identity,
        loading: false,
        error: null,
        signIn: vi.fn(),
        clearIdentity: vi.fn(),
        refreshIdentity: () => setIdentity({ userId: "user-1", token: "id-token" }),
        authClient: mockAuthClient,
      };
    },
  };
});

vi.mock("@/api/auth", () => ({ loginWithShoo: mockLoginWithShoo }));

describe("LoginPage", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/auth/callback?code=code&state=state");
    sessionStorage.clear();
    sessionStorage.setItem("kestrel_auth_return_to", "/settings");
    mockAuthClient.parseCallback.mockReturnValue({ code: "code", state: "state" });
    mockAuthClient.finishSignIn.mockResolvedValue({ pairwise_sub: "user-1", id_token: "id-token" });
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
    expect(await screen.findByText("Settings")).toBeInTheDocument();
    expect(sessionStorage.getItem("kestrel_auth_return_to")).toBeNull();
  });
});
