import { describe, expect, it } from "vitest";
import { leadDisplayStage, mapLeadDetail, mapLeadSummary } from "@/lib/leads-map";

describe("leads-map", () => {
  it("maps list summary snake_case to Lead", () => {
    const lead = mapLeadSummary({
      id: "abc",
      name: "Priya",
      status: "IN_PROGRESS",
      intent_label: "HOT",
      score: 87,
      service_interest: "Website",
      source: "AD",
      last_inbound_at: "2026-08-20T10:00:00Z",
      meeting_status: "NOT_REQUESTED",
      do_not_contact: false,
    });
    expect(lead).toMatchObject({
      id: "abc",
      status: "IN_PROGRESS",
      intentLabel: "HOT",
      score: 87,
      source: "AD",
    });
    expect(leadDisplayStage(lead)).toBe("HOT");
  });

  it("maps detail with thread messages and consent", () => {
    const detail = mapLeadDetail({
      id: "abc",
      name: "Priya",
      status: "NEW",
      intent_label: null,
      score: 40,
      memory_facts: [
        { id: "f1", category: "budget", fact: "₹50k", source: "stated", confidence: 90 },
      ],
      conversation: {
        id: "c1",
        messages: [
          {
            id: "m1",
            role: "user",
            content: "Hi",
            timestamp: "2026-08-20T10:00:00Z",
            status: "received",
          },
          {
            id: "m2",
            role: "agent",
            content: "Hello",
            timestamp: "2026-08-20T10:01:00Z",
            status: "sent",
          },
        ],
      },
      consent: {
        id: "co1",
        source: "inbound",
        granted_at: "2026-08-20T09:00:00Z",
      },
    });
    expect(detail.memoryFacts).toHaveLength(1);
    expect(detail.messages).toHaveLength(2);
    expect(detail.messages[0].role).toBe("user");
    expect(detail.messages[1].role).toBe("agent");
    expect(detail.conversationId).toBe("c1");
    expect(detail.consentLabel).toContain("Opt-in");
  });
});
