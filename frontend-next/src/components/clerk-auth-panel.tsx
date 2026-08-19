"use client";

import { SignIn, SignUp } from "@clerk/nextjs";

/** Renders Clerk's hosted sign-in / sign-up widget with PATH routing so Clerk's
 * multi-step sub-paths (e.g. /signup/sso-callback, /login/factor-one) resolve.
 * Requires the page to be a catch-all route ([[...rest]]). Only rendered when
 * Clerk is active. Post-auth redirects come from the NEXT_PUBLIC_CLERK_* env vars. */
export function ClerkAuthPanel({ mode }: { mode: "sign-in" | "sign-up" }) {
  return mode === "sign-in" ? (
    <SignIn path="/login" routing="path" signUpUrl="/signup" />
  ) : (
    <SignUp path="/signup" routing="path" signInUrl="/login" />
  );
}
