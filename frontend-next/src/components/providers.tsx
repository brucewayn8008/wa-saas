"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Toaster } from "sonner";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import { ClerkApiBridge } from "@/components/clerk-api-bridge";

type ProvidersProps = {
  children: React.ReactNode;
  withClerk?: boolean;
};

export function Providers({ children, withClerk = false }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <NuqsAdapter>
        {/* Registers Clerk's getToken with the API client. Inside <ClerkProvider> (root layout). */}
        {withClerk ? <ClerkApiBridge /> : null}
        {children}
        <Toaster richColors position="top-right" />
      </NuqsAdapter>
    </QueryClientProvider>
  );
}
