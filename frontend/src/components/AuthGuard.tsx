/** Reject anonymous application-page access. */

import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { fetchAuthState } from "@/api/auth";
import { setDefaultProfileId } from "@/api/applications";

export function AuthGuard() {
  const location = useLocation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchAuthState,
    staleTime: 30_000,
    retry: false,
  });

  if (isPending) return null;
  if (isError || (!data?.authenticated && data?.auth_required !== false)) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  if (data?.authenticated) setDefaultProfileId(data.profile_id);
  return <Outlet />;
}
