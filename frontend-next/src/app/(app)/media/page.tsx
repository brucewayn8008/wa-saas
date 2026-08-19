"use client";

import { useMemo, useState } from "react";
import { ImageIcon } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { MediaGrid } from "@/components/media/media-grid";
import { UsageMeter } from "@/components/billing/usage-meter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useBilling, useMedia } from "@/hooks/use-settings";

const filters = ["All", "Images", "Videos"] as const;

export default function MediaPage() {
  const { data, isLoading, isError, refetch } = useMedia();
  const billing = useBilling();
  const [filter, setFilter] = useState<(typeof filters)[number]>("All");

  const assets = useMemo(() => {
    if (!data) return [];
    if (filter === "Images") return data.filter((a) => a.type === "image");
    if (filter === "Videos") return data.filter((a) => a.type === "video");
    return data;
  }, [data, filter]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Media"
        description="Brand media library — tenant-owned photos and videos the agent can send. No real-person persona photos."
        actions={<Button>Upload</Button>}
      />

      {billing.data ? (
        <Card>
          <CardContent className="pt-6">
            <UsageMeter
              label="Storage"
              used={billing.data.usage.mediaStoredMb}
              quota={billing.data.usage.mediaQuotaMb}
              unit=" MB"
            />
          </CardContent>
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-1.5">
        {filters.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-[var(--radius-full)] px-3 py-1.5 text-[var(--text-xs)] font-[var(--font-semibold)] ${
              filter === f
                ? "bg-[var(--brand)] text-[var(--brand-fg)]"
                : "bg-[var(--surface-2)] text-[var(--fg-muted)]"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="aspect-video" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={ImageIcon}
          title="Couldn’t load media"
          description="Try again shortly."
          actionLabel="Retry"
          onAction={() => refetch()}
        />
      ) : assets.length === 0 ? (
        <EmptyState
          icon={ImageIcon}
          title="No media yet"
          description="Upload portfolio or product assets for the agent to share in conversations."
          actionLabel="Upload"
        />
      ) : (
        <>
          <MediaGrid assets={assets} />
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-10 text-center">
              <p className="text-[var(--text-sm)] font-[var(--font-semibold)] text-[var(--fg)]">
                Drop files to upload
              </p>
              <p className="mt-1 text-[var(--text-xs)] text-[var(--fg-muted)]">
                Images and videos only — brand assets you own.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
