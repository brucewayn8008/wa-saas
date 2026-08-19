/** CRM pipeline status (backend `Lead.status`). */
export type LeadStatus = "NEW" | "IN_PROGRESS" | "CONVERTED" | "FAILED";
/** Buying-intent label (backend `Lead.intent_label`). */
export type LeadIntent = "HOT" | "WARM" | "COLD";
/** Visual badge values — intent or status that StageBadge can render. */
export type LeadStage = "NEW" | "HOT" | "WARM" | "COLD" | "CONVERTED" | "FAILED";
export type LeadSource = "DIRECT" | "GROUP" | "AD" | "WIDGET";
export type WaStatus = "UNCONFIGURED" | "QR_PENDING" | "CONNECTED" | "LOGGED_OUT";
export type TemplateStatus = "pending" | "approved" | "rejected";
export type MemberRole = "owner" | "admin" | "agent";
export type MessageRole = "user" | "agent" | "human";

export type DashboardData = {
  companyName: string;
  agentEnabled: boolean;
  waStatus: WaStatus;
  usage: {
    conversationsUsed: number;
    conversationsQuota: number;
    messagesSent: number;
    mediaStoredMb: number;
    mediaQuotaMb: number;
  };
  stats: {
    activeConversations: number;
    hotLeads: number;
    meetingsBookedWeek: number;
    messagesSentToday: number;
  };
  activity: ActivityItem[];
  needsAttention: NeedsAttentionItem[];
};

export type ActivityItem = {
  id: string;
  title: string;
  detail: string;
  eventType: string;
  createdAt: string;
};

export type NeedsAttentionItem = {
  id: string;
  kind: "listening" | "takeover";
  title: string;
  href: string;
};

export type ConversationSummary = {
  id: string;
  leadId: string;
  contactName: string;
  lastMessage: string;
  updatedAt: string;
  stage: LeadStage;
  unread: number;
  humanTakeover: boolean;
  within24hWindow: boolean;
  doNotContact: boolean;
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  text: string;
  timestamp: string;
  status?: "sent" | "delivered" | "read";
};

export type ConversationDetail = ConversationSummary & {
  messages: ChatMessage[];
  score: number;
};

export type Lead = {
  id: string;
  name: string;
  phoneMasked?: string;
  status: LeadStatus;
  intentLabel: LeadIntent | null;
  score: number;
  serviceInterest: string;
  source: LeadSource;
  lastInboundAt: string | null;
  meetingStatus: string;
  doNotContact: boolean;
  requirementSummary?: string;
};

export type MemoryFact = {
  id: string;
  category: string;
  fact: string;
  source: "stated" | "inferred";
  confidence?: number | null;
};

export type LeadDetail = Lead & {
  memoryFacts: MemoryFact[];
  messages: ChatMessage[];
  conversationId?: string;
  consentLabel?: string;
};

export type LeadListFilters = {
  status?: LeadStatus | "";
  intent?: LeadIntent | "";
  source?: LeadSource | "";
  minScore?: number | null;
  search?: string;
};

export type LeadListResult = {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
};

export type LeadPatch = {
  status?: LeadStatus;
  intentLabel?: LeadIntent | null;
  doNotContact?: boolean;
};

export type ListeningItem = {
  id: string;
  groupName: string;
  originalMessage: string;
  matchReason: "keyword" | "semantic";
  /** Automated reply text (field name kept for mock compatibility). */
  draftReply: string;
  createdAt: string;
  status: "detected" | "sent" | "blocked" | "dismissed";
  blockReason?: string | null;
  leadId?: string | null;
};

export type MessageTemplate = {
  id: string;
  name: string;
  language: string;
  status: TemplateStatus;
  body: string;
  lastUsedAt?: string;
};

export type MediaAsset = {
  id: string;
  type: "image" | "video";
  name: string;
  tags: string[];
  usedByAgent: boolean;
  url: string;
  sizeMb: number;
};

export type TeamMember = {
  id: string;
  email: string;
  role: MemberRole;
  name: string;
};

export type AgentSettings = {
  brandName: string;
  businessDescription: string;
  services: string[];
  tone: string;
  offer: string;
  bookingLink: string;
  businessHours: string;
  disclosureLine: string;
  agentEnabled: boolean;
};

export type BillingInfo = {
  plan: string;
  status: string;
  renewDate: string;
  priceLabel: string;
  usage: {
    conversationsUsed: number;
    conversationsQuota: number;
    numbersUsed: number;
    numbersQuota: number;
    seatsUsed: number;
    seatsQuota: number;
    mediaStoredMb: number;
    mediaQuotaMb: number;
  };
};

export type ApiResult<T> = {
  success: boolean;
  data?: T;
  error?: string;
};
