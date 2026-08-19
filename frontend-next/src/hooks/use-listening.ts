"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { dismissListening, fetchListening } from "@/lib/services";

export function useListening() {
  return useQuery({
    queryKey: queryKeys.listening,
    queryFn: fetchListening,
  });
}

export function useDismissListening() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => dismissListening(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.listening }),
  });
}
