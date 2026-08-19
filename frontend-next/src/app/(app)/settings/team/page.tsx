"use client";

import Link from "next/link";
import { Users } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useTeam } from "@/hooks/use-settings";

export default function TeamSettingsPage() {
  const { data, isLoading, isError, refetch } = useTeam();

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" asChild>
        <Link href="/settings">Back to settings</Link>
      </Button>
      <PageHeader
        title="Team"
        description="Members and roles — owner, admin, or agent."
        actions={<Button disabled>Invite member</Button>}
      />

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-14" />
              ))}
            </div>
          ) : isError ? (
            <div className="p-4">
              <EmptyState
                icon={Users}
                title="Couldn’t load team"
                description="Try again shortly."
                actionLabel="Retry"
                onAction={() => refetch()}
              />
            </div>
          ) : (
            <table className="w-full text-left text-[var(--text-sm)]">
              <thead className="border-b border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg-muted)]">
                <tr>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Name</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Email</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Role</th>
                </tr>
              </thead>
              <tbody>
                {data?.map((member) => (
                  <tr key={member.id} className="border-b border-[var(--border)]">
                    <td className="px-4 py-3 font-[var(--font-semibold)]">{member.name}</td>
                    <td className="px-4 py-3 text-[var(--fg-muted)]">{member.email}</td>
                    <td className="px-4 py-3">
                      <Badge variant="outline">{member.role}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
