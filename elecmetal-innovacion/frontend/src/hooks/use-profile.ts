"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMe } from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";
import type { UserProfile } from "@/lib/types";

export const PROFILE_KEY = ["profile"] as const;

export function useProfile() {
  return useQuery<UserProfile>({
    queryKey: PROFILE_KEY,
    queryFn: async () => {
      const token = await getAccessToken();
      return fetchMe(token);
    },
  });
}
