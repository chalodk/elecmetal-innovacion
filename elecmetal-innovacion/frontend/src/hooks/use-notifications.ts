"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listNotifications, processNotifications } from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";

// ═════════════════════════════════════════════════════════════════════════════
// Notifications List
// ═════════════════════════════════════════════════════════════════════════════

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: async () => {
      const result = await listNotifications(await getAccessToken());
      return Array.isArray(result) ? result : (result.data ?? []);
    },
  });
}

// ═════════════════════════════════════════════════════════════════════════════
// Process Notifications
// ═════════════════════════════════════════════════════════════════════════════

export function useProcessNotifications() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => processNotifications(await getAccessToken()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
