import { fireEvent, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Layout } from "@/components/Layout";
import { renderWithProviders } from "@/test-utils";

vi.mock("@/api/onboarding", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/onboarding")>();
  return {
    ...actual,
    fetchOnboardingStatus: vi.fn().mockResolvedValue({
      completed_at: new Date().toISOString(),
      welcome_completed_at: new Date().toISOString(),
    }),
    patchOnboardingStep: vi.fn().mockResolvedValue({}),
  };
});

function renderWithRouter(initialEntries: string[] = ["/"]) {
  return renderWithProviders(<Layout />, {
    route: initialEntries[0],
    routerProps: { initialEntries },
  });
}

describe("Layout", () => {
  it("renders the Kestrel branding", () => {
    renderWithRouter();
    expect(screen.getByText("Kestrel")).toBeInTheDocument();
  });

  it("renders Pipeline navigation link", () => {
    renderWithRouter();
    expect(screen.getByText("Pipeline")).toBeInTheDocument();
  });

  it("renders Analytics navigation link", () => {
    renderWithRouter();
    expect(screen.getByText("Analytics")).toBeInTheDocument();
  });

  it("renders Follow-Ups navigation link", () => {
    renderWithRouter();
    expect(screen.getByText("Follow-Ups")).toBeInTheDocument();
  });

  it("renders Settings navigation link", () => {
    renderWithRouter();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("highlights active nav item", () => {
    renderWithRouter(["/"]);
    const pipelineLink = screen.getByText("Pipeline").closest("a");
    expect(pipelineLink).toHaveClass("bg-gray-100");
  });

  it("toggles accessible mobile navigation and closes after navigation", () => {
    renderWithRouter();
    const toggle = screen.getByRole("button", { name: "Open navigation menu" });
    const navigation = screen.getByRole("navigation").querySelector("#primary-navigation");

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(navigation).toHaveClass("hidden");

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Close navigation menu" })).toBeInTheDocument();
    expect(navigation).toHaveClass("block");

    fireEvent.click(screen.getByRole("link", { name: "Settings" }));
    expect(screen.getByRole("button", { name: "Open navigation menu" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
});
