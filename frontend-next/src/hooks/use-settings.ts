"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { fetchBilling, fetchMedia, fetchSettings, fetchTeam, fetchTemplates, saveSettings } from "@/lib/services";
import type { AgentSettings } from "@/types";

export function useSettings() {
  return useQuery({ queryKey: queryKeys.settings, queryFn: fetchSettings });
}

export function useSaveSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (settings: AgentSettings) => saveSettings(settings),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.settings });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useTeam() {
  return useQuery({ queryKey: queryKeys.team, queryFn: fetchTeam });
}

export function useTemplates() {
  return useQuery({ queryKey: queryKeys.templates, queryFn: fetchTemplates });
}

export function useMedia() {
  return useQuery({ queryKey: queryKeys.media, queryFn: fetchMedia });
}

export function useBilling() {
  return useQuery({ queryKey: queryKeys.billing, queryFn: fetchBilling });
}
