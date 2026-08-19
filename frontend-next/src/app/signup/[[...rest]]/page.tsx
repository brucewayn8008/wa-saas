import Link from "next/link";
import { AUTH_BYPASS } from "@/lib/config";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ClerkAuthPanel } from "@/components/clerk-auth-panel";

// Catch-all so Clerk's sub-paths (e.g. /signup/sso-callback, /signup/verify-email-address) resolve.
export default function SignupPage() {
  if (!AUTH_BYPASS) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-4">
        <ClerkAuthPanel mode="sign-up" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create your PrePop workspace</CardTitle>
          <CardDescription>Dev mode — skip to onboarding without Clerk.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button asChild className="w-full">
            <Link href="/onboarding">Continue to onboarding</Link>
          </Button>
          <Button variant="ghost" asChild className="w-full">
            <Link href="/login">Already have an account?</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
