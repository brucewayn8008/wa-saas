"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { fetchLead, fetchLeads, patchLead } from "@/lib/services";
import type { LeadDetail, LeadListFilters, LeadPatch } from "@/types";

export function useLeads(filters: LeadListFilters = {}) {
  const keyFilters: Record<string, string> = {};
  if (filters.status) keyFilters.status = filters.status;
  if (filters.intent) keyFilters.intent = filters.intent;
  if (filters.source) keyFilters.source = filters.source;
  if (filters.minScore != null && filters.minScore > 0) {
    keyFilters.minScore = String(filters.minScore);
  }
  if (filters.search?.trim()) keyFilters.search = filters.search.trim();

  return useQuery({
    queryKey: queryKeys.leads(keyFilters),
    queryFn: () => fetchLeads(filters),
  });
}

export function useLead(id: string) {
  return useQuery({
    queryKey: queryKeys.lead(id),
    queryFn: () => fetchLead(id),
    enabled: !!id,
  });
}

export function usePatchLead(id: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (patch: LeadPatch) => patchLead(id, patch),
    onMutate: async (patch) => {
      await qc.cancelQueries({ queryKey: queryKeys.lead(id) });
      const previous = qc.getQueryData<LeadDetail>(queryKeys.lead(id));
      if (previous) {
        qc.setQueryData<LeadDetail>(queryKeys.lead(id), {
          ...previous,
          ...(patch.status !== undefined ? { status: patch.status } : {}),
          ...(patch.intentLabel !== undefined ? { intentLabel: patch.intentLabel } : {}),
          ...(patch.doNotContact !== undefined
            ? { doNotContact: patch.doNotContact }
            : {}),
        });
      }
      return { previous };
    },
    onError: (_err, _patch, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(queryKeys.lead(id), ctx.previous);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: queryKeys.lead(id) });
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
  });
}
