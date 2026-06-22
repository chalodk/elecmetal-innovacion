"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMessages } from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";
import type { Message } from "@/lib/types";

export const MESSAGES_KEY = (sessionId: number | string) => ["messages", sessionId] as const;

export function useMessages(sessionId: number | string) {
  return useQuery<Message[]>({
    queryKey: MESSAGES_KEY(sessionId),
    queryFn: async () => {
      const token = await getAccessToken();
      const res = await fetchMessages(token, Number(sessionId), { limit: 100 });
      return res.data;
    },
    enabled: !!sessionId,
  });
}
