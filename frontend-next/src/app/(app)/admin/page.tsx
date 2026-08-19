import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Admin"
        description="Staff-only super-admin console. Hidden from tenant navigation."
      />
      <Card>
        <CardHeader>
          <CardTitle>Placeholder</CardTitle>
        </CardHeader>
        <CardContent className="text-[var(--text-sm)] text-[var(--fg-muted)]">
          Tenant health, usage, and support tools will land here when the backend admin API is
          ready. This route is not linked in the sidebar.
        </CardContent>
      </Card>
    </div>
  );
}
