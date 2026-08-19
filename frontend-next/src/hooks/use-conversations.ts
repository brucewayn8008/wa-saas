"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import {
  fetchConversation,
  fetchConversations,
  sendConversationReply,
  setTakeover,
} from "@/lib/services";

export function useConversations() {
  return useQuery({
    queryKey: queryKeys.conversations,
    queryFn: fetchConversations,
  });
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: queryKeys.conversation(id),
    queryFn: () => fetchConversation(id),
    enabled: !!id,
  });
}

export function useSendReply(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => sendConversationReply(id, text),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.conversation(id) });
      qc.invalidateQueries({ queryKey: queryKeys.conversations });
    },
  });
}

export function useTakeover(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) => setTakeover(id, enabled),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.conversation(id) });
      qc.invalidateQueries({ queryKey: queryKeys.conversations });
    },
  });
}
