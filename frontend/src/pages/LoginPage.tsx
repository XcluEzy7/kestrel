/** Shoo Google sign-in page establishing Kestrel server session. */

import { useEffect, useRef, useState } from "react";
import { useShooAuth } from "@shoojs/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { fetchAuthState, loginWithDebug, loginWithShoo } from "@/api/auth";

const RETURN_TO_STORAGE_KEY = "kestrel_auth_return_to";

function safeReturnTo(value: string | null, fallback: string): string {
  if (!value) return fallback;
  try {
    const target = new URL(value, window.location.origin);
    if (target.origin !== window.location.origin) return fallback;
    const route = `${target.pathname}${target.search}${target.hash}`;
    return route.startsWith("/") && !route.startsWith("//") ? route : fallback;
  } catch {
    return fallback;
  }
}

export function LoginPage() {
  const {
    identity,
    loading,
    error,
    signIn,
    clearIdentity,
    refreshIdentity,
    authClient,
  } = useShooAuth({
    autoHandleCallback: false,
    returnToStorageKey: RETURN_TO_STORAGE_KEY,
  });
  const [serverError, setServerError] = useState<string | null>(null);
  const [debugSecret, setDebugSecret] = useState("");
  const [debugBusy, setDebugBusy] = useState(false);
  const submittedToken = useRef<string | null>(null);
  const callbackHandled = useRef(false);
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { data: authState } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchAuthState,
    retry: false,
  });
  const from = safeReturnTo(
    (location.state as { from?: string } | null)?.from ?? null,
    "/",
  );
  const callbackPending = authClient?.parseCallback() !== null;

  useEffect(() => {
    if (loading || !authClient || callbackHandled.current || !callbackPending) {
      return;
    }
    callbackHandled.current = true;
    void authClient
      .finishSignIn({ redirectAfter: false, consumeReturnTo: false })
      .then(() => refreshIdentity())
      .catch(() => {
        clearIdentity();
        setServerError("Sign-in could not be completed. Try again.");
      });
  }, [authClient, callbackPending, clearIdentity, loading, refreshIdentity]);

  useEffect(() => {
    if (loading || callbackPending || !identity.token || submittedToken.current === identity.token) return;
    submittedToken.current = identity.token;
    const returnTo = safeReturnTo(
      sessionStorage.getItem(RETURN_TO_STORAGE_KEY),
      from,
    );
    void loginWithShoo(identity.token)
      .then((state) => {
        queryClient.setQueryData(["auth", "me"], state);
        sessionStorage.removeItem(RETURN_TO_STORAGE_KEY);
        navigate(returnTo, { replace: true });
      })
      .catch(() => {
        clearIdentity();
        setServerError("Sign-in could not be verified. Try again.");
      });
  }, [callbackPending, clearIdentity, from, identity.token, loading, navigate, queryClient]);

  const submitDebugLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setDebugBusy(true);
    setServerError(null);
    try {
      const state = await loginWithDebug(debugSecret);
      queryClient.setQueryData(["auth", "me"], state);
      setDebugSecret("");
      navigate(from, { replace: true });
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Debug sign-in failed");
    } finally {
      setDebugBusy(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <section className="w-full max-w-sm rounded-xl border bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-gray-900">Sign in to Kestrel</h1>
        <p className="mt-2 text-sm text-gray-600">Use Google through Shoo to protect your job-search data.</p>
        {(error || serverError) && (
          <p role="alert" className="mt-4 text-sm text-red-700">{serverError ?? error}</p>
        )}
        <button
          type="button"
          disabled={loading}
          onClick={() => void signIn({ returnTo: from })}
          className="mt-6 w-full rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading || identity.token ? "Signing in..." : "Continue with Google"}
        </button>
        {authState?.debug_auth_enabled && (
          <form className="mt-6 border-t pt-6" onSubmit={submitDebugLogin}>
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Non-production debug access</p>
            <p className="mt-1 text-xs text-gray-600">Use only for controlled frontend testing. This creates an isolated debug profile.</p>
            <label className="mt-3 block text-sm font-medium text-gray-700">
              Debug secret
              <input
                type="password"
                required
                value={debugSecret}
                onChange={(event) => setDebugSecret(event.target.value)}
                className="mt-1 w-full rounded-md border px-3 py-2"
                autoComplete="off"
              />
            </label>
            <button
              type="submit"
              disabled={debugBusy}
              className="mt-3 w-full rounded-md border border-amber-600 px-4 py-2 text-sm font-medium text-amber-800 disabled:opacity-50"
            >
              {debugBusy ? "Signing in..." : "Continue with debug access"}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
