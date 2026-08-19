import type {
  ChatMessage,
  Lead,
  LeadDetail,
  LeadIntent,
  LeadSource,
  LeadStage,
  LeadStatus,
  MemoryFact,
  MessageRole,
} from "@/types";

/** API wire shapes (snake_case from FastAPI). */
type ApiLeadSummary = {
  id: string;
  name: string;
  status: string;
  intent_label?: string | null;
  score?: number | null;
  service_interest?: string | null;
  source?: string | null;
  last_inbound_at?: string | null;
  meeting_status?: string | null;
  do_not_contact?: boolean;
  requirement_summary?: string | null;
};

type ApiMemoryFact = {
  id: string;
  category?: string | null;
  fact: string;
  confidence?: number | null;
  source?: string | null;
};

type ApiThreadMessage = {
  id: string;
  direction?: string;
  role: string;
  content: string;
  timestamp?: string | null;
  status?: string | null;
};

type ApiConsent = {
  id: string;
  source: string;
  granted_at?: string | null;
  revoked_at?: string | null;
};

type ApiConversation = {
  id: string;
  status?: string;
  human_takeover?: boolean;
  last_inbound_at?: string | null;
  messages?: ApiThreadMessage[];
};

type ApiLeadDetail = ApiLeadSummary & {
  memory_facts?: ApiMemoryFact[];
  conversation?: ApiConversation | null;
  consent?: ApiConsent | null;
};

const STATUSES = new Set<LeadStatus>(["NEW", "IN_PROGRESS", "CONVERTED", "FAILED"]);
const INTENTS = new Set<LeadIntent>(["HOT", "WARM", "COLD"]);
const SOURCES = new Set<LeadSource>(["DIRECT", "GROUP", "AD", "WIDGET"]);

function asStatus(raw: string | null | undefined): LeadStatus {
  const v = (raw || "NEW").toUpperCase();
  return STATUSES.has(v as LeadStatus) ? (v as LeadStatus) : "NEW";
}

function asIntent(raw: string | null | undefined): LeadIntent | null {
  if (!raw) return null;
  const v = raw.toUpperCase();
  return INTENTS.has(v as LeadIntent) ? (v as LeadIntent) : null;
}

function asSource(raw: string | null | undefined): LeadSource {
  const v = (raw || "DIRECT").toUpperCase();
  return SOURCES.has(v as LeadSource) ? (v as LeadSource) : "DIRECT";
}

function asMessageRole(raw: string): MessageRole {
  if (raw === "agent" || raw === "human") return raw;
  return "user";
}

function asMessageStatus(
  raw: string | null | undefined
): ChatMessage["status"] | undefined {
  if (!raw) return undefined;
  const v = raw.toLowerCase();
  if (v === "sent" || v === "delivered" || v === "read") return v;
  if (v === "received") return "delivered";
  return undefined;
}

function formatConsentLabel(consent: ApiConsent | null | undefined): string | undefined {
  if (!consent || consent.revoked_at) return undefined;
  const when = consent.granted_at
    ? new Date(consent.granted_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      })
    : null;
  return when ? `Opt-in · ${consent.source} · ${when}` : `Opt-in · ${consent.source}`;
}

export function mapLeadSummary(raw: ApiLeadSummary): Lead {
  return {
    id: String(raw.id),
    name: raw.name || "Unknown",
    status: asStatus(raw.status),
    intentLabel: asIntent(raw.intent_label),
    score: Math.max(0, Math.min(100, Number(raw.score ?? 0))),
    serviceInterest: raw.service_interest || "—",
    source: asSource(raw.source),
    lastInboundAt: raw.last_inbound_at ?? null,
    meetingStatus: raw.meeting_status || "NOT_REQUESTED",
    doNotContact: Boolean(raw.do_not_contact),
    requirementSummary: raw.requirement_summary ?? undefined,
  };
}

function mapMemoryFact(raw: ApiMemoryFact): MemoryFact {
  const src = (raw.source || "stated").toLowerCase();
  return {
    id: String(raw.id),
    category: raw.category || "general",
    fact: raw.fact,
    source: src === "inferred" ? "inferred" : "stated",
    confidence: raw.confidence ?? null,
  };
}

function mapThreadMessage(raw: ApiThreadMessage): ChatMessage {
  return {
    id: String(raw.id),
    role: asMessageRole(raw.role),
    text: raw.content || "",
    timestamp: raw.timestamp || new Date(0).toISOString(),
    status: asMessageStatus(raw.status),
  };
}

export function mapLeadDetail(raw: ApiLeadDetail): LeadDetail {
  const base = mapLeadSummary(raw);
  const convo = raw.conversation;
  return {
    ...base,
    memoryFacts: (raw.memory_facts ?? []).map(mapMemoryFact),
    messages: (convo?.messages ?? []).map(mapThreadMessage),
    conversationId: convo?.id ? String(convo.id) : undefined,
    consentLabel: formatConsentLabel(raw.consent),
  };
}

/** Prefer intent for the stage badge; fall back to status when StageBadge supports it. */
export function leadDisplayStage(lead: Pick<Lead, "status" | "intentLabel">): LeadStage | null {
  if (lead.intentLabel) return lead.intentLabel;
  if (lead.status === "NEW" || lead.status === "CONVERTED" || lead.status === "FAILED") {
    return lead.status;
  }
  return null;
}
