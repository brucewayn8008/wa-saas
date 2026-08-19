"use client";

import { CreditCard } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { UsageMeter } from "@/components/billing/usage-meter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useBilling } from "@/hooks/use-settings";
import { toast } from "sonner";

export default function BillingPage() {
  const { data, isLoading, isError, refetch } = useBilling();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={CreditCard}
        title="Couldn’t load billing"
        description="Try again shortly."
        actionLabel="Retry"
        onAction={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Billing"
        description="Plan, usage meters, and invoices."
        actions={
          <Button
            onClick={() => toast.message("Stripe portal opens when billing API is wired")}
          >
            Upgrade
          </Button>
        }
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>{data.plan}</CardTitle>
            <p className="text-[var(--text-sm)] text-[var(--fg-muted)]">{data.priceLabel}</p>
          </div>
          <Badge variant="success">{data.status}</Badge>
        </CardHeader>
        <CardContent className="text-[var(--text-sm)] text-[var(--fg-muted)]">
          Renews {data.renewDate}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Usage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <UsageMeter
            label="Conversations"
            used={data.usage.conversationsUsed}
            quota={data.usage.conversationsQuota}
          />
          <UsageMeter
            label="Connected numbers"
            used={data.usage.numbersUsed}
            quota={data.usage.numbersQuota}
          />
          <UsageMeter
            label="Seats"
            used={data.usage.seatsUsed}
            quota={data.usage.seatsQuota}
          />
          <UsageMeter
            label="Media storage"
            used={data.usage.mediaStoredMb}
            quota={data.usage.mediaQuotaMb}
            unit=" MB"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Invoices</CardTitle>
        </CardHeader>
        <CardContent className="text-[var(--text-sm)] text-[var(--fg-muted)]">
          Invoice history appears here after Stripe is connected.
        </CardContent>
      </Card>
    </div>
  );
}
