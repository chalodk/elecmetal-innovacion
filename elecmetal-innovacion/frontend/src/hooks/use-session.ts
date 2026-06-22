"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSession } from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";
import type { Session } from "@/lib/types";

export const SESSION_KEY = (id: number) => ["session", id] as const;

export function useSession(id: number) {
  return useQuery<Session>({
    queryKey: SESSION_KEY(id),
    queryFn: async () => {
      const token = await getAccessToken();
      return fetchSession(token, id);
    },
    enabled: !!id,
  });
}
