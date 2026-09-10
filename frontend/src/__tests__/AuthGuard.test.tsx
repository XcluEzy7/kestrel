/** Authentication guard route-matrix tests. */

import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthGuard } from "@/components/AuthGuard";
import { renderWithProviders } from "@/test-utils";

const mockFetchAuthState = vi.fn();
vi.mock("@/api/auth", () => ({ fetchAuthState: () => mockFetchAuthState() }));

describe("AuthGuard", () => {
  beforeEach(() => mockFetchAuthState.mockReset());

  it("redirects anonymous private route to login", async () => {
    mockFetchAuthState.mockResolvedValue({ authenticated: false });
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<div>Login</div>} />
        <Route element={<AuthGuard />}><Route path="/private" element={<div>Private</div>} /></Route>
      </Routes>,
      { route: "/private" },
    );
    expect(await screen.findByText("Login")).toBeInTheDocument();
    expect(screen.queryByText("Private")).not.toBeInTheDocument();
  });

  it("renders private route after authenticated profile resolves", async () => {
    mockFetchAuthState.mockResolvedValue({ authenticated: true, profile_id: 7 });
    renderWithProviders(
      <Routes><Route element={<AuthGuard />}><Route path="/private" element={<div>Private</div>} /></Route></Routes>,
      { route: "/private" },
    );
    expect(await screen.findByText("Private")).toBeInTheDocument();
    expect(mockFetchAuthState).toHaveBeenCalledTimes(1);
  });

  it("renders private route when server reports local auth disabled", async () => {
    mockFetchAuthState.mockResolvedValue({ authenticated: false, auth_required: false });
    renderWithProviders(
      <Routes><Route element={<AuthGuard />}><Route path="/private" element={<div>Private</div>} /></Route></Routes>,
      { route: "/private" },
    );
    expect(await screen.findByText("Private")).toBeInTheDocument();
  });
});
