"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchInitiatives } from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";
import type { InitiativeStatus } from "@/lib/types";

export const INITIATIVES_KEY = ["initiatives"] as const;

export function useInitiatives(params?: {
  status?: InitiativeStatus;
  cursor?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: [...INITIATIVES_KEY, params],
    queryFn: async () => {
      const token = await getAccessToken();
      const res = await fetchInitiatives(token, params);
      return res;
    },
  });
}
