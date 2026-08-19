import type { Metadata } from "next";
import { SiteNav } from "@/components/relay-landing/navigation/SiteNav";
import { Hero } from "@/components/relay-landing/hero/Hero";
import { Manifesto } from "@/components/relay-landing/sections/Manifesto";
import { Problem } from "@/components/relay-landing/sections/Problem";
import { Agent } from "@/components/relay-landing/sections/Agent";
import { HowItWorks } from "@/components/relay-landing/sections/HowItWorks";
import { RealConversation } from "@/components/relay-landing/sections/RealConversation";
import { HumanDifference } from "@/components/relay-landing/sections/HumanDifference";
import { Infrastructure } from "@/components/relay-landing/sections/Infrastructure";
import { UseCases } from "@/components/relay-landing/sections/UseCases";
import { Economics } from "@/components/relay-landing/sections/Economics";
import { Results } from "@/components/relay-landing/metrics/Results";
import { FinalCta } from "@/components/relay-landing/cta/FinalCta";
import { SiteFooter } from "@/components/relay-landing/footer/SiteFooter";
import "./landing.css";

export const metadata: Metadata = {
  title: "PrePop — Autonomous WhatsApp Sales Infrastructure",
  description:
    "Turn WhatsApp into your autonomous sales team. Find prospects, qualify leads, handle objections, and follow up automatically.",
};

export default function MarketingHomePage() {
  return (
    <div className="relay-landing">
      <SiteNav />
      <main>
        <Hero />
        <Manifesto />
        <Problem />
        <Agent />
        <HowItWorks />
        <RealConversation />
        <HumanDifference />
        <Infrastructure />
        <UseCases />
        <Economics />
        <Results />
        <FinalCta />
      </main>
      <SiteFooter />
    </div>
  );
}
