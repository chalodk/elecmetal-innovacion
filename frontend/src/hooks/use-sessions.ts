"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchSessions, createSession } from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";
import type { Session, AgentType } from "@/lib/types";

export const SESSIONS_KEY = ["sessions"] as const;

export function useSessions() {
  return useQuery<Session[]>({
    queryKey: SESSIONS_KEY,
    queryFn: async () => {
      const token = await getAccessToken();
      const res = await fetchSessions(token);
      return res.data;
    },
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (agentType: AgentType) => {
      const token = await getAccessToken();
      return createSession(token, agentType);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });
}
