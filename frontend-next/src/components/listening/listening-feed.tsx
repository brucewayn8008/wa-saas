"use client";

import { useEffect } from "react";
import { Ear } from "lucide-react";
import { toast } from "sonner";
import { ApprovalCard } from "@/components/listening/approval-card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useDismissListening, useListening } from "@/hooks/use-listening";

export function ListeningFeed() {
  const { data, isLoading, isError, refetch } = useListening();
  const dismiss = useDismissListening();

  useEffect(() => {
    if (isError) {
      toast.error("Couldn’t load listening inbox");
    }
  }, [isError]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-56" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <EmptyState
        icon={Ear}
        title="Couldn’t load listening inbox"
        description="Try again in a moment."
        actionLabel="Retry"
        onAction={() => refetch()}
      />
    );
  }

  if (!data?.length) {
    return (
      <EmptyState
        icon={Ear}
        title="Nothing to review"
        description="When the agent detects a matching group ask and replies to the lead, it will show up here."
      />
    );
  }

  return (
    <div className="space-y-4">
      {data.map((item) => (
        <ApprovalCard
          key={item.id}
          item={item}
          onDismiss={(id) =>
            dismiss.mutate(id, {
              onSuccess: () => toast.message("Removed from inbox"),
              onError: (e) => toast.error(e.message),
            })
          }
          dismissing={dismiss.isPending && dismiss.variables === item.id}
        />
      ))}
    </div>
  );
}
