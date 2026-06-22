"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchInitiative } from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";
import type { Initiative } from "@/lib/types";

export const INITIATIVE_KEY = (id: number) => ["initiatives", id] as const;

export function useInitiative(id: number) {
  return useQuery<Initiative>({
    queryKey: INITIATIVE_KEY(id),
    queryFn: async () => {
      const token = await getAccessToken();
      return fetchInitiative(token, id);
    },
    enabled: !!id,
  });
}
