import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import type { MediaAsset } from "@/types";

export function MediaGrid({ assets }: { assets: MediaAsset[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {assets.map((asset) => (
        <article
          key={asset.id}
          className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]"
        >
          <div className="relative aspect-video bg-[var(--surface-2)]">
            <Image
              src={asset.url}
              alt={asset.name}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 25vw"
              unoptimized
            />
          </div>
          <div className="space-y-2 p-3">
            <p className="truncate text-[var(--text-sm)] font-[var(--font-semibold)] text-[var(--fg)]">
              {asset.name}
            </p>
            <div className="flex flex-wrap gap-1">
              <Badge variant="outline">{asset.type}</Badge>
              {asset.tags.map((tag) => (
                <Badge key={tag} variant="brand">
                  {tag}
                </Badge>
              ))}
              {asset.usedByAgent ? <Badge variant="success">Used by agent</Badge> : null}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
