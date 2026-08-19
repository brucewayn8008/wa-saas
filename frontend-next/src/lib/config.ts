export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const USE_MOCKS =
  process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

export const CLERK_PUBLISHABLE_KEY =
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";

/** Dev bypass when Clerk keys are missing */
export const AUTH_BYPASS =
  !CLERK_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_AUTH_BYPASS === "true";
