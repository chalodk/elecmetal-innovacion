"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  triggerEvaluation,
  getEvaluationByInitiative,
  reviewEvaluation,
  updateInitiativeStatus,
} from "@/lib/api";
import { getAccessToken } from "@/lib/get-token";

// ═════════════════════════════════════════════════════════════════════════════
// Trigger Evaluation
// ═════════════════════════════════════════════════════════════════════════════

export function useTriggerEvaluation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (initiativeId: number | string) => {
      return triggerEvaluation(
        await getAccessToken(),
        String(initiativeId),
      );
    },
    onSuccess: (_data, initiativeId) => {
      queryClient.invalidateQueries({ queryKey: ["initiatives"] });
      queryClient.invalidateQueries({
        queryKey: ["evaluation", initiativeId],
      });
    },
  });
}

// ═════════════════════════════════════════════════════════════════════════════
// Evaluation by Initiative
// ═════════════════════════════════════════════════════════════════════════════

export function useEvaluationByInitiative(initiativeId: number | string) {
  return useQuery({
    queryKey: ["evaluation", initiativeId],
    queryFn: async () =>
      getEvaluationByInitiative(await getAccessToken(), String(initiativeId)),
    enabled: !!initiativeId,
    retry: false, // 404 (no evaluation yet) → null
  });
}

// ═════════════════════════════════════════════════════════════════════════════
// Update Initiative Status
// ═════════════════════════════════════════════════════════════════════════════

export function useUpdateInitiativeStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      initiativeId,
      status,
    }: {
      initiativeId: number | string;
      status: string;
    }) => {
      return updateInitiativeStatus(
        await getAccessToken(),
        String(initiativeId),
        status,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["initiatives"] });
    },
  });
}

// ═════════════════════════════════════════════════════════════════════════════
// Review Evaluation
// ═════════════════════════════════════════════════════════════════════════════

export function useReviewEvaluation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      evaluationId,
      veredicto,
      validate,
    }: {
      evaluationId: number | string;
      veredicto?: string;
      validate?: boolean;
    }) => {
      return reviewEvaluation(await getAccessToken(), String(evaluationId), {
        veredicto,
        validate,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluation"] });
      queryClient.invalidateQueries({ queryKey: ["initiatives"] });
    },
  });
}
