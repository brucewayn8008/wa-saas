import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { ListeningFeed } from "@/components/listening/listening-feed";
import { Skeleton } from "@/components/ui/skeleton";

export default function ListeningPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Listening"
        description="The agent watches groups you belong to, detects buying intent, and automatically replies to the lead on your behalf. Review what was sent here."
      />

      <Suspense
        fallback={
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-56" />
            ))}
          </div>
        }
      >
        <ListeningFeed />
      </Suspense>
    </div>
  );
}
