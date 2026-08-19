import { apiFetch, USE_MOCKS } from "@/lib/api";
import {
  mockBilling,
  mockConversationDetails,
  mockConversations,
  mockDashboard,
  mockMedia,
  mockSettings,
  mockTeam,
  mockTemplates,
} from "@/lib/mock/data";
import { mapLeadDetail, mapLeadSummary } from "@/lib/leads-map";
import type {
  AgentSettings,
  BillingInfo,
  ConversationDetail,
  ConversationSummary,
  DashboardData,
  Lead,
  LeadDetail,
  LeadListFilters,
  LeadListResult,
  LeadPatch,
  ListeningItem,
  MediaAsset,
  MessageTemplate,
  TeamMember,
} from "@/types";

type ApiLeadRow = Parameters<typeof mapLeadSummary>[0];
type ApiLeadDetailRow = Parameters<typeof mapLeadDetail>[0];

type ApiListeningRow = {
  id: string;
  group_name: string;
  original_message: string;
  match_reason: string;
  match_score?: number | null;
  reply_text?: string | null;
  status: string;
  block_reason?: string | null;
  created_at?: string | null;
  lead_id?: string | null;
};

const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms));

function mapListeningItem(row: ApiListeningRow): ListeningItem {
  const reason = (row.match_reason || "keyword").toLowerCase();
  const status = (row.status || "detected").toLowerCase();
  const allowedStatus = new Set(["detected", "sent", "blocked", "dismissed"]);
  return {
    id: row.id,
    groupName: row.group_name,
    originalMessage: row.original_message,
    matchReason: reason === "semantic" ? "semantic" : "keyword",
    draftReply: row.reply_text || "",
    createdAt: row.created_at || new Date().toISOString(),
    status: (allowedStatus.has(status) ? status : "detected") as ListeningItem["status"],
    blockReason: row.block_reason ?? null,
    leadId: row.lead_id ?? null,
  };
}
export async function fetchDashboard(): Promise<DashboardData> {
  if (USE_MOCKS) {
    await delay();
    return mockDashboard;
  }
  const res = await apiFetch<DashboardData>("/api/v1/dashboard");
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load dashboard");
  return res.data;
}

export async function fetchConversations(): Promise<ConversationSummary[]> {
  if (USE_MOCKS) {
    await delay();
    return mockConversations;
  }
  const res = await apiFetch<ConversationSummary[]>("/api/v1/conversations");
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load conversations");
  return res.data;
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  if (USE_MOCKS) {
    await delay();
    const detail = mockConversationDetails[id];
    if (!detail) throw new Error("Conversation not found");
    return structuredClone(detail);
  }
  const res = await apiFetch<ConversationDetail>(`/api/v1/conversations/${id}`);
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load conversation");
  return res.data;
}

export async function sendConversationReply(id: string, text: string): Promise<void> {
  if (USE_MOCKS) {
    await delay(200);
    const detail = mockConversationDetails[id];
    if (detail) {
      detail.messages.push({
        id: `local-${Date.now()}`,
        role: "human",
        text,
        timestamp: new Date().toISOString(),
        status: "sent",
      });
      detail.lastMessage = text;
      detail.humanTakeover = true;
    }
    return;
  }
  const res = await apiFetch(`/api/v1/conversations/${id}/messages`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  if (!res.success) throw new Error(res.error || "Failed to send");
}

export async function setTakeover(id: string, enabled: boolean): Promise<void> {
  if (USE_MOCKS) {
    await delay(150);
    const detail = mockConversationDetails[id];
    if (detail) detail.humanTakeover = enabled;
    const summary = mockConversations.find((c) => c.id === id);
    if (summary) summary.humanTakeover = enabled;
    return;
  }
  const res = await apiFetch(`/api/v1/conversations/${id}/takeover`, {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
  if (!res.success) throw new Error(res.error || "Failed to update takeover");
}

/**
 * Leads CRM is live even while `NEXT_PUBLIC_USE_MOCKS=true` elsewhere (Feature 15b).
 * Full mock flip is deferred to prompt 07.
 */
function leadsQueryString(filters: LeadListFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.intent) params.set("intent_label", filters.intent);
  if (filters.source) params.set("source", filters.source);
  if (filters.minScore != null && filters.minScore > 0) {
    params.set("min_score", String(filters.minScore));
  }
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchLeads(filters: LeadListFilters = {}): Promise<LeadListResult> {
  const res = await apiFetch<{
    items: ApiLeadRow[];
    total: number;
    limit: number;
    offset: number;
  }>(`/api/v1/leads${leadsQueryString(filters)}`);
  if (!res.success || !res.data) throw new Error("Failed to load leads");
  const items = (res.data.items ?? []).map(mapLeadSummary);
  return {
    items,
    total: Number(res.data.total ?? items.length),
    limit: Number(res.data.limit ?? items.length),
    offset: Number(res.data.offset ?? 0),
  };
}

export async function fetchLead(id: string): Promise<LeadDetail> {
  const res = await apiFetch<ApiLeadDetailRow>(`/api/v1/leads/${id}`);
  if (!res.success || !res.data) throw new Error("Failed to load lead");
  return mapLeadDetail(res.data);
}

export async function patchLead(id: string, patch: LeadPatch): Promise<Lead> {
  const body: Record<string, unknown> = {};
  if (patch.status !== undefined) body.status = patch.status;
  if (patch.intentLabel !== undefined) body.intent_label = patch.intentLabel;
  if (patch.doNotContact !== undefined) body.do_not_contact = patch.doNotContact;

  const res = await apiFetch<ApiLeadRow>(`/api/v1/leads/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!res.success || !res.data) throw new Error("Failed to update lead");
  return mapLeadSummary(res.data);
}

export async function fetchListening(): Promise<ListeningItem[]> {
  /**
   * Listening inbox is live even while `NEXT_PUBLIC_USE_MOCKS=true` elsewhere (Feature 16b).
   * Full mock flip is deferred to prompt 07.
   */
  const res = await apiFetch<ApiListeningRow[]>("/api/v1/listening");
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load listening");
  return res.data.map(mapListeningItem);
}

export async function dismissListening(id: string): Promise<void> {
  const res = await apiFetch(`/api/v1/listening/${id}`, { method: "DELETE" });
  if (!res.success) throw new Error(res.error || "Failed to dismiss");
}

export async function fetchTemplates(): Promise<MessageTemplate[]> {
  if (USE_MOCKS) {
    await delay();
    return mockTemplates;
  }
  const res = await apiFetch<MessageTemplate[]>("/api/v1/templates");
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load templates");
  return res.data;
}

export async function fetchMedia(): Promise<MediaAsset[]> {
  if (USE_MOCKS) {
    await delay();
    return mockMedia;
  }
  const res = await apiFetch<MediaAsset[]>("/api/v1/media");
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load media");
  return res.data;
}

export async function fetchSettings(): Promise<AgentSettings> {
  if (USE_MOCKS) {
    await delay();
    return { ...mockSettings };
  }
  const res = await apiFetch<AgentSettings>("/api/v1/settings");
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load settings");
  return res.data;
}

export async function saveSettings(settings: AgentSettings): Promise<AgentSettings> {
  if (USE_MOCKS) {
    await delay(300);
    Object.assign(mockSettings, settings);
    return { ...mockSettings };
  }
  const res = await apiFetch<AgentSettings>("/api/v1/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
  if (!res.success || !res.data) throw new Error(res.error || "Failed to save settings");
  return res.data;
}

export async function fetchTeam(): Promise<TeamMember[]> {
  if (USE_MOCKS) {
    await delay();
    return mockTeam;
  }
  const res = await apiFetch<TeamMember[]>("/api/v1/settings/team");
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load team");
  return res.data;
}

export async function fetchBilling(): Promise<BillingInfo> {
  if (USE_MOCKS) {
    await delay();
    return mockBilling;
  }
  const res = await apiFetch<BillingInfo>("/api/v1/billing");
  if (!res.success || !res.data) throw new Error(res.error || "Failed to load billing");
  return res.data;
}

export async function setAgentEnabled(enabled: boolean): Promise<void> {
  if (USE_MOCKS) {
    await delay(150);
    mockDashboard.agentEnabled = enabled;
    mockSettings.agentEnabled = enabled;
    return;
  }
  const res = await apiFetch("/api/v1/settings/agent", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
  if (!res.success) throw new Error(res.error || "Failed to update agent");
}
