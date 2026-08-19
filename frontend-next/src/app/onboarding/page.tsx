"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { Check, Loader2, Rocket, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

type QrStatus = "idle" | "loading" | "qr_ready" | "connected" | "error";

const steps = ["Connect WhatsApp", "Configure agent", "Go live"] as const;

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [qrStatus, setQrStatus] = useState<QrStatus>("idle");
  const [qrValue, setQrValue] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const pollQr = useCallback(async () => {
    try {
      const res = await apiFetch<{ status: string; qr: string | null }>("/api/v1/onboarding/qr");
      if (!res.success || !res.data) return;
      const { status, qr } = res.data;
      if (status === "CONNECTED") {
        setQrStatus("connected");
        stopPolling();
        // Auto-advance after brief delay so user sees the success state
        setTimeout(() => setStep(1), 1200);
      } else if (qr) {
        setQrStatus("qr_ready");
        setQrValue(qr);
      } else {
        setQrStatus("loading");
      }
    } catch {
      setQrStatus("error");
    }
  }, []);

  useEffect(() => {
    if (step !== 0) return;
    const kickoff = window.setTimeout(() => {
      void pollQr();
      pollRef.current = setInterval(() => {
        void pollQr();
      }, 4000);
    }, 0);
    return () => {
      clearTimeout(kickoff);
      stopPolling();
    };
  }, [step, pollQr]);

  return (
    <div className="min-h-screen bg-[var(--bg)] px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 flex items-center gap-2">
          <div className="rounded-[var(--radius-md)] bg-[var(--brand)] p-2 text-[var(--brand-fg)]">
            <Rocket className="h-4 w-4" aria-hidden="true" />
          </div>
          <span className="font-[var(--font-bold)] text-[var(--fg)]">PrePop onboarding</span>
        </div>

        <ol className="mb-8 flex flex-wrap gap-2" aria-label="Onboarding steps">
          {steps.map((label, i) => (
            <li
              key={label}
              className={cn(
                "flex items-center gap-1.5 rounded-[var(--radius-full)] px-3 py-1.5 text-[var(--text-xs)] font-[var(--font-semibold)]",
                i < step
                  ? "bg-[var(--success-subtle)] text-[var(--success)]"
                  : i === step
                    ? "bg-[var(--brand)] text-[var(--brand-fg)]"
                    : "bg-[var(--surface-2)] text-[var(--fg-subtle)]"
              )}
            >
              {i < step ? <Check className="h-3 w-3" aria-hidden="true" /> : null}
              {i + 1}. {label}
            </li>
          ))}
        </ol>

        {/* Step 0 — Connect WhatsApp via wacli QR */}
        {step === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>Connect your WhatsApp number</CardTitle>
              <CardDescription>
                Scan the QR code with WhatsApp on your phone to link your number.
                This uses a linked-device session — your number stays yours.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
                {/* QR panel */}
                <div className="flex h-[188px] w-[188px] shrink-0 items-center justify-center rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-3">
                  {qrStatus === "connected" ? (
                    <div className="flex flex-col items-center gap-2 text-[var(--success)]">
                      <Wifi className="h-10 w-10" />
                      <span className="text-[var(--text-sm)] font-[var(--font-semibold)]">Connected!</span>
                    </div>
                  ) : qrStatus === "error" ? (
                    <div className="flex flex-col items-center gap-2 text-[var(--fg-muted)]">
                      <WifiOff className="h-8 w-8" />
                      <span className="text-[var(--text-xs)] text-center">Gateway unavailable</span>
                    </div>
                  ) : qrStatus === "qr_ready" && qrValue ? (
                    <QRCodeSVG value={qrValue} size={160} />
                  ) : (
                    <div className="flex flex-col items-center gap-3 text-[var(--fg-muted)]">
                      <Loader2 className="h-8 w-8 animate-spin" />
                      <span className="text-[var(--text-xs)]">Generating QR…</span>
                    </div>
                  )}
                </div>

                <div className="space-y-3 text-[var(--text-sm)] text-[var(--fg-muted)]">
                  <p className="font-[var(--font-semibold)] text-[var(--fg)]">How to scan</p>
                  <ol className="list-decimal space-y-1.5 pl-4">
                    <li>Open WhatsApp on your phone</li>
                    <li>Tap <strong>Linked devices</strong> → <strong>Link a device</strong></li>
                    <li>Point your camera at the QR code</li>
                  </ol>
                  <p className="text-[var(--text-xs)] text-[var(--fg-subtle)]">
                    We never cold-message strangers. The agent always discloses it&apos;s AI.
                  </p>
                </div>
              </div>

              {qrStatus === "connected" ? (
                <p className="text-[var(--text-sm)] text-[var(--success)] font-[var(--font-semibold)]">
                  WhatsApp connected — advancing…
                </p>
              ) : (
                <Button variant="secondary" onClick={() => setStep(1)}>
                  Skip for now →
                </Button>
              )}
            </CardContent>
          </Card>
        ) : null}

        {/* Step 1 — Configure agent persona */}
        {step === 1 ? (
          <Card>
            <CardHeader>
              <CardTitle>Configure your agent</CardTitle>
              <CardDescription>Persona, services offered, and mandatory AI disclosure.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="company">Company / brand name</Label>
                <Input id="company" placeholder="Northline Studio" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="services">What do you sell?</Label>
                <Input id="services" placeholder="Website design, landing pages, branding" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="disclosure">AI disclosure line</Label>
                <Textarea
                  id="disclosure"
                  placeholder="Hi — I'm an AI assistant for Northline Studio. How can I help?"
                  rows={2}
                />
                <p className="text-[var(--text-xs)] text-[var(--fg-subtle)]">
                  This line is sent at the start of every new conversation. Required.
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="booking">Booking / calendar link</Label>
                <Input id="booking" type="url" placeholder="https://cal.com/yourname" />
              </div>
              <Button onClick={() => setStep(2)}>Continue →</Button>
            </CardContent>
          </Card>
        ) : null}

        {/* Step 2 — Go live */}
        {step === 2 ? (
          <Card>
            <CardHeader>
              <CardTitle>You&apos;re ready to go live</CardTitle>
              <CardDescription>
                Flip the agent on from your dashboard and start answering inbound
                WhatsApp chats automatically.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href="/dashboard">Go to dashboard →</Link>
              </Button>
              <Button variant="secondary" asChild>
                <Link href="/settings">Edit settings</Link>
              </Button>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
