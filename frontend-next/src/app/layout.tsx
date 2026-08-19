import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { ClerkProvider } from "@clerk/nextjs";
import { Providers } from "@/components/providers";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PrePop — WhatsApp AI Sales Agent",
  description: "Disclosed AI sales agent for WhatsApp. Qualify leads, share media, book meetings.",
};

// Clerk's <ClerkProvider> needs per-request auth context; force dynamic rendering
// so static prerender doesn't fail on Clerk hooks (useAuth/SignIn).
export const dynamic = "force-dynamic";

// Clerk is active only when a publishable key is present and bypass is off.
const CLERK_ACTIVE =
  Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) &&
  process.env.NEXT_PUBLIC_AUTH_BYPASS !== "true";

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const tree = (
    <html lang="en">
      <body className={`${inter.variable} ${GeistSans.variable} ${GeistMono.variable} font-sans antialiased`}>
        <Providers withClerk={CLERK_ACTIVE}>{children}</Providers>
      </body>
    </html>
  );

  // ClerkProvider must wrap the app from a SERVER component (this layout) so it can
  // inject request auth state that client hooks (useAuth/SignIn) rely on.
  return CLERK_ACTIVE ? <ClerkProvider>{tree}</ClerkProvider> : tree;
}
