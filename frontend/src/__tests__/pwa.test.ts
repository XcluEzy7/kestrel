import { afterEach, describe, expect, it, vi } from "vitest";
import { registerServiceWorker } from "@/pwa";

describe("PWA shell", () => {
  afterEach(() => {
    delete (navigator as Navigator & { serviceWorker?: unknown }).serviceWorker;
  });

  it("registers the app-shell service worker after page load", () => {
    const register = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: { register },
    });

    registerServiceWorker();
    window.dispatchEvent(new Event("load"));

    expect(register).toHaveBeenCalledWith("/sw.js");
  });
});
