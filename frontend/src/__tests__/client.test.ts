/** Session fetch and CSRF tests. */

import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch, csrfToken } from "@/api/client";

describe("apiFetch", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("adds same-origin credentials and CSRF to mutations", async () => {
    Object.defineProperty(document, "cookie", { configurable: true, value: "kestrel_csrf=csrf-value" });
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/private", { method: "POST", headers: { "Content-Type": "application/json" } });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.credentials).toBe("same-origin");
    expect(new Headers(init.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });

  it("does not add CSRF to safe requests", async () => {
    Object.defineProperty(document, "cookie", { configurable: true, value: "kestrel_csrf=value" });
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/private");
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(csrfToken()).toBe("value");
    expect(new Headers(init.headers).has("X-CSRF-Token")).toBe(false);
  });
});
