import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Clerk is active only when a publishable key is present and bypass is off.
const CLERK_ACTIVE =
  Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) &&
  process.env.NEXT_PUBLIC_AUTH_BYPASS !== "true";

const LEGACY_REDIRECTS = new Set(["/groups", "/outreach", "/workspaces"]);

const isProtected = createRouteMatcher([
  "/dashboard(.*)",
  "/onboarding(.*)",
  "/conversations(.*)",
  "/leads(.*)",
  "/listening(.*)",
  "/templates(.*)",
  "/media(.*)",
  "/settings(.*)",
  "/billing(.*)",
  "/admin(.*)",
]);

function legacyRedirect(req: NextRequest): NextResponse | null {
  if (LEGACY_REDIRECTS.has(req.nextUrl.pathname)) {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }
  return null;
}

// Real Clerk middleware: enables server-side auth() / getToken() and protects app routes.
const clerkHandler = clerkMiddleware(async (auth, req) => {
  const redirect = legacyRedirect(req as unknown as NextRequest);
  if (redirect) return redirect;
  if (isProtected(req)) {
    const { userId } = await auth();
    if (!userId) {
      const signIn = new URL("/login", req.url);
      signIn.searchParams.set("redirect_url", req.nextUrl.pathname);
      return NextResponse.redirect(signIn);
    }
  }
});

// Passthrough for keyless / bypass local development.
function passthrough(req: NextRequest) {
  return legacyRedirect(req) ?? NextResponse.next();
}

export default CLERK_ACTIVE ? clerkHandler : passthrough;

export const config = {
  matcher: [
    // Skip Next internals and static files; run on everything else + API.
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
