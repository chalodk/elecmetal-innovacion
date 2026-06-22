"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchMessages, sendMessage } from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";
import type { Message } from "@/lib/types";

export const MESSAGES_KEY = (sessionId: number) => ["messages", sessionId] as const;

export function useMessages(sessionId: number) {
  return useQuery<Message[]>({
    queryKey: MESSAGES_KEY(sessionId),
    queryFn: async () => {
      const token = await getAccessToken();
      const res = await fetchMessages(token, sessionId, { limit: 100 });
      return res.data;
    },
    enabled: !!sessionId,
  });
}

export function useSendMessage(sessionId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (content: string) => {
      const token = await getAccessToken();
      return sendMessage(token, sessionId, content);
    },
    onSuccess: (data) => {
      queryClient.setQueryData<Message[]>(
        MESSAGES_KEY(sessionId),
        (old = []) => {
          const newMessages = [data.user_message];
          if (data.assistant_message) {
            newMessages.push(data.assistant_message);
          }
          return [...(old || []), ...newMessages];
        },
      );
    },
  });
}
