"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { fetchDashboard, setAgentEnabled } from "@/lib/services";

export function useDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: fetchDashboard,
  });
}

export function useToggleAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) => setAgentEnabled(enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.dashboard }),
  });
}
