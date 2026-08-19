export const queryKeys = {
  dashboard: ["dashboard"] as const,
  conversations: ["conversations"] as const,
  conversation: (id: string) => ["conversations", id] as const,
  leads: (filters?: Record<string, string>) => ["leads", filters ?? {}] as const,
  lead: (id: string) => ["leads", id] as const,
  listening: ["listening"] as const,
  templates: ["templates"] as const,
  media: ["media"] as const,
  settings: ["settings"] as const,
  team: ["team"] as const,
  billing: ["billing"] as const,
};
