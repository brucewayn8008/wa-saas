import Link from "next/link";
import { AUTH_BYPASS } from "@/lib/config";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ClerkAuthPanel } from "@/components/clerk-auth-panel";

// Catch-all so Clerk's sub-paths (e.g. /login/factor-one, /login/sso-callback) resolve.
export default function LoginPage() {
  if (!AUTH_BYPASS) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-4">
        <ClerkAuthPanel mode="sign-in" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Log in to PrePop</CardTitle>
          <CardDescription>Auth bypass is on for local development.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button asChild className="w-full">
            <Link href="/dashboard">Continue to dashboard</Link>
          </Button>
          <Button variant="secondary" asChild className="w-full">
            <Link href="/signup">Create an account</Link>
          </Button>
          <Button variant="ghost" asChild className="w-full">
            <Link href="/">Back to home</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
