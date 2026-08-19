"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Settings as SettingsIcon } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useSaveSettings, useSettings } from "@/hooks/use-settings";
import { settingsSchema, type SettingsFormValues } from "@/lib/validators/settings";

export default function SettingsPage() {
  const { data, isLoading, isError, refetch } = useSettings();
  const save = useSaveSettings();

  const form = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      brandName: "",
      businessDescription: "",
      services: [],
      tone: "friendly_professional",
      offer: "",
      bookingLink: "",
      businessHours: "",
      disclosureLine: "",
      agentEnabled: false,
    },
  });

  useEffect(() => {
    if (data) {
      form.reset({
        ...data,
        services: data.services,
      });
    }
  }, [data, form]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (isError) {
    return (
      <EmptyState
        icon={SettingsIcon}
        title="Couldn’t load settings"
        description="Try again shortly."
        actionLabel="Retry"
        onAction={() => refetch()}
      />
    );
  }

  const onSubmit = form.handleSubmit((values) => {
    save.mutate(values, {
      onSuccess: () => toast.success("Settings saved"),
      onError: (e) => toast.error(e.message),
    });
  });

  const servicesValue = form.watch("services");
  const disclosure = form.watch("disclosureLine");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Agent persona, services, hours, and mandatory AI disclosure."
        actions={
          <Button variant="secondary" asChild>
            <Link href="/settings/team">Team</Link>
          </Button>
        }
      />

      <form onSubmit={onSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Business profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="brandName">Brand name</Label>
              <Input id="brandName" {...form.register("brandName")} />
              <p className="text-[var(--text-xs)] text-[var(--danger)]">
                {form.formState.errors.brandName?.message}
              </p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="businessDescription">Business description</Label>
              <Textarea id="businessDescription" {...form.register("businessDescription")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="services">Services (comma-separated)</Label>
              <Input
                id="services"
                value={Array.isArray(servicesValue) ? servicesValue.join(", ") : ""}
                onChange={(e) =>
                  form.setValue(
                    "services",
                    e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                    { shouldValidate: true }
                  )
                }
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="tone">Tone</Label>
                <Input id="tone" {...form.register("tone")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="businessHours">Business hours</Label>
                <Input id="businessHours" {...form.register("businessHours")} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="offer">Offer</Label>
              <Input id="offer" {...form.register("offer")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="bookingLink">Booking link</Label>
              <Input id="bookingLink" {...form.register("bookingLink")} />
            </div>
          </CardContent>
        </Card>

        <Card className="border-[var(--brand)]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              AI disclosure
              <Badge variant="danger">Required</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-[var(--text-sm)] text-[var(--fg-muted)]">
              Shown at the start of new conversations. The agent must disclose it is AI.
            </p>
            <Label htmlFor="disclosureLine">Disclosure line</Label>
            <Textarea id="disclosureLine" {...form.register("disclosureLine")} />
            <p className="text-[var(--text-xs)] text-[var(--danger)]">
              {form.formState.errors.disclosureLine?.message}
            </p>
            <div className="rounded-[var(--radius-lg)] bg-[var(--bubble-out-bg)] px-3.5 py-2.5">
              <Badge variant="brand" className="mb-1.5">
                AI
              </Badge>
              <p className="text-[var(--text-sm)]">{disclosure || "Disclosure preview…"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between pt-6">
            <div>
              <p className="font-[var(--font-semibold)]">Agent enabled</p>
              <p className="text-[var(--text-sm)] text-[var(--fg-muted)]">
                When on, the agent auto-replies within the compliance gate.
              </p>
            </div>
            <Switch
              checked={form.watch("agentEnabled")}
              onCheckedChange={(v) => form.setValue("agentEnabled", v)}
              aria-label="Agent enabled"
            />
          </CardContent>
        </Card>

        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save changes"}
        </Button>
      </form>
    </div>
  );
}
