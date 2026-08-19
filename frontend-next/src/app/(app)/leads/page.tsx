import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { LeadsBoard } from "@/components/leads/leads-board";

export default function LeadsPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Leads"
        description="CRM for inbound and consented leads — scored and staged by the agent."
        actions={
          <Button variant="secondary" disabled>
            Export
          </Button>
        }
      />

      <Suspense
        fallback={
          <div className="space-y-3">
            <Skeleton className="h-10 max-w-sm" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        }
      >
        <LeadsBoard />
      </Suspense>
    </div>
  );
}
