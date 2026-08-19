"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { setApiTokenGetter } from "@/lib/api";

/**
 * Registers Clerk's `getToken` with the API client so every `/api/v1` request
 * carries the session JWT (verified by the FastAPI backend via JWKS).
 * Rendered only inside <ClerkProvider>.
 */
export function ClerkApiBridge() {
  const { getToken } = useAuth();

  useEffect(() => {
    setApiTokenGetter(() => getToken());
    return () => setApiTokenGetter(null);
  }, [getToken]);

  return null;
}
