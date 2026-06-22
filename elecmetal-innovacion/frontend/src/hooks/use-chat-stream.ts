"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAccessToken } from "@/lib/get-token";
import { sendMessage } from "@/lib/api";
import { createSSEStream } from "@/lib/sse-client";
import { MESSAGES_KEY } from "@/hooks/use-messages";
import type { Message } from "@/lib/types";

interface UseChatStreamReturn {
  /** Contenido del mensaje del asistente en construcción */
  streamingMessage: string | null;
  /** true mientras el stream está activo */
  isStreaming: boolean;
  /** Mensaje de error si el stream falló */
  streamError: string | null;
  /** Envía un mensaje e inicia el stream */
  send: (content: string) => Promise<void>;
  /** Cancela el stream activo */
  cancelStream: () => void;
  /** Reintenta el último stream fallido */
  retryStream: () => void;
}

const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 1000;

/** ID temporal para mensajes generados por streaming (no persistidos aún) */
let optimisticIdCounter = -1;
function nextOptimisticId(): number {
  return optimisticIdCounter--;
}

export function useChatStream(sessionId: number): UseChatStreamReturn {
  const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const abortRef = useRef<(() => void) | null>(null);
  const retryCountRef = useRef(0);
  const accumulatedTokensRef = useRef<string[]>([]);
  const lastUserMessageRef = useRef<Message | null>(null);

  // Ref para permitir recursión dentro de startStream sin stale closure
  const startStreamRef = useRef<(tokenCount?: number) => Promise<void>>(async () => {});

  const cancelStream = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;
    setIsStreaming(false);
    setStreamingMessage(null);
    setStreamError(null);
  }, []);

  const startStream = useCallback(
    async (tokenCount: number = 0) => {
      setIsStreaming(true);
      setStreamError(null);

      try {
        const token = await getAccessToken();
        const { stream, abort } = createSSEStream(
          sessionId,
          token,
          tokenCount > 0 ? tokenCount : undefined,
        );
        abortRef.current = abort;

        const reader = stream.getReader();
        const localTokens: string[] = tokenCount > 0 ? [...accumulatedTokensRef.current] : [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          localTokens.push(value);
          accumulatedTokensRef.current = localTokens;
          setStreamingMessage(localTokens.join(""));
        }

        // Stream completado exitosamente — guardar mensaje en cache
        const fullContent = localTokens.join("");
        retryCountRef.current = 0;
        accumulatedTokensRef.current = [];

        // Agregar el mensaje completo del asistente al cache como optimista
        const optimisticAssistant: Message = {
          id: nextOptimisticId(),
          session_id: sessionId,
          role: "assistant",
          content: fullContent,
          metadata: null,
          created_at: new Date().toISOString(),
        };

        queryClient.setQueryData<Message[]>(
          MESSAGES_KEY(sessionId),
          (old = []) => [...(old || []), optimisticAssistant],
        );

        setIsStreaming(false);
        setStreamingMessage(null);

        // Refetch en segundo plano para sincronizar con el backend
        // (cuando A2 esté listo, el backend tendrá el mensaje real)
        queryClient.invalidateQueries({ queryKey: MESSAGES_KEY(sessionId) });
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          setIsStreaming(false);
          return;
        }

        // Error de stream — intentar reconexión
        if (retryCountRef.current < MAX_RETRIES) {
          retryCountRef.current += 1;
          const delay = RETRY_BASE_DELAY_MS * Math.pow(2, retryCountRef.current - 1);
          const currentTokens = accumulatedTokensRef.current.length;

          setStreamError(`Reconectando en ${delay / 1000}s... (intento ${retryCountRef.current}/${MAX_RETRIES})`);

          setTimeout(() => {
            startStreamRef.current(currentTokens);
          }, delay);
        } else {
          setStreamError(
            "Error de conexión con Clara. Verifica tu internet e intenta de nuevo.",
          );
          setIsStreaming(false);
        }
      }
    },
    [sessionId, queryClient],
  );

  // Mantener el ref actualizado (fuera del render path, en efecto)
  useEffect(() => {
    startStreamRef.current = startStream;
  });

  const send = useCallback(
    async (content: string) => {
      // Cancelar cualquier stream activo
      cancelStream();

      // Resetear estado
      accumulatedTokensRef.current = [];
      retryCountRef.current = 0;
      setStreamingMessage(null);
      setStreamError(null);

      // Agregar el user_message al cache optimistamente (inmediato)
      const optimisticId = nextOptimisticId();
      const optimisticUserMsg: Message = {
        id: optimisticId,
        session_id: sessionId,
        role: "user",
        content,
        metadata: null,
        created_at: new Date().toISOString(),
      };

      queryClient.setQueryData<Message[]>(
        MESSAGES_KEY(sessionId),
        (old = []) => [...(old || []), optimisticUserMsg],
      );

      try {
        const token = await getAccessToken();

        // Enviar al backend en segundo plano (persiste user + placeholder)
        const response = await sendMessage(token, sessionId, content);

        // Reemplazar el mensaje optimista con el real del backend
        queryClient.setQueryData<Message[]>(
          MESSAGES_KEY(sessionId),
          (old = []) =>
            (old || []).map((msg) =>
              msg.id === optimisticId ? response.user_message : msg,
            ),
        );

        lastUserMessageRef.current = response.user_message;

        // Iniciar el stream para obtener la respuesta de Clara
        startStream();
      } catch {
        setStreamError("Error al enviar el mensaje. Intenta de nuevo.");
        // Revertir mensaje optimista
        queryClient.setQueryData<Message[]>(
          MESSAGES_KEY(sessionId),
          (old = []) => (old || []).filter((msg) => msg.id !== optimisticId),
        );
      }
    },
    [sessionId, cancelStream, startStream, queryClient],
  );

  const retryStream = useCallback(() => {
    // Reintenta el stream desde el último punto de acumulación
    setStreamError(null);
    startStream(accumulatedTokensRef.current.length);
  }, [startStream]);

  return {
    streamingMessage,
    isStreaming,
    streamError,
    send,
    cancelStream,
    retryStream,
  };
}
