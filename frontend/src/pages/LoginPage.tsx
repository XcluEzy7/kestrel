/** Shoo Google sign-in page establishing Kestrel server session. */

import { useEffect, useRef, useState } from "react";
import { useShooAuth } from "@shoojs/react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { loginWithShoo } from "@/api/auth";

export function LoginPage() {
  const { identity, loading, error, signIn, clearIdentity } = useShooAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const submittedToken = useRef<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  useEffect(() => {
    if (!identity.token || submittedToken.current === identity.token) return;
    submittedToken.current = identity.token;
    void loginWithShoo(identity.token)
      .then((state) => {
        queryClient.setQueryData(["auth", "me"], state);
        navigate(from, { replace: true });
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
