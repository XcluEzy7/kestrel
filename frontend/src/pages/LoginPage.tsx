/** Shoo Google sign-in page establishing Kestrel server session. */

import { useEffect, useRef, useState } from "react";
import { useShooAuth } from "@shoojs/react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { loginWithShoo } from "@/api/auth";

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
  const submittedToken = useRef<string | null>(null);
  const callbackHandled = useRef(false);
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  useEffect(() => {
    if (loading || !authClient || callbackHandled.current || !authClient.parseCallback()) {
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
  }, [authClient, clearIdentity, loading, refreshIdentity]);

  useEffect(() => {
    if (!identity.token || submittedToken.current === identity.token) return;
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
  }, [clearIdentity, from, identity.token, navigate, queryClient]);

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
      </section>
    </main>
  );
}
