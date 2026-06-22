"use client";

import { useSession } from "@/hooks/use-session";
import { useMessages } from "@/hooks/use-messages";
import { useChatStream } from "@/hooks/use-chat-stream";
import MessageList from "./message-list";
import ChatInput from "./chat-input";
import Link from "next/link";

interface ChatViewProps {
  sessionId: number;
}

function agentLabel(type: string): string {
  return type === "clara" ? "Clara" : "Analista de Oportunidad";
}

export default function ChatView({ sessionId }: ChatViewProps) {
  const {
    data: session,
    isLoading: sessionLoading,
    isError: sessionError,
    error: sessionErr,
  } = useSession(sessionId);

  const {
    data: messages,
    isLoading: messagesLoading,
    isError: messagesError,
    refetch: refetchMessages,
  } = useMessages(sessionId);

  const {
    streamingMessage,
    isStreaming,
    streamError,
    send,
    retryStream,
  } = useChatStream(sessionId);

  // ── Session-level errors (404, 403) ──────────────────────────
  if (sessionError) {
    const apiError = sessionErr as { status?: number; message?: string } | null;
    const isForbidden = apiError?.status === 403;

    return (
      <div className="rounded-lg border bg-white p-8 text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <svg className="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-900">
          {isForbidden
            ? "No tienes acceso a esta sesión"
            : "La sesión no existe o fue eliminada"}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          {isForbidden
            ? "Esta sesión pertenece a otro usuario."
            : "Es posible que el enlace sea incorrecto."}
        </p>
        <Link
          href="/dashboard"
          className="mt-4 inline-block text-sm text-blue-600 hover:underline"
        >
          Volver al inicio
        </Link>
      </div>
    );
  }

  // ── Loading skeleton ─────────────────────────────────────────
  const isLoading = sessionLoading || messagesLoading;

  if (isLoading) {
    return (
      <div className="flex flex-col h-[calc(100vh-12rem)] rounded-lg border bg-white">
        {/* Header skeleton */}
        <div className="border-b px-4 py-3">
          <div className="h-5 w-32 animate-pulse rounded bg-gray-200" />
          <div className="mt-1 h-3 w-20 animate-pulse rounded bg-gray-100" />
        </div>
        {/* Message skeletons */}
        <div className="flex-1 space-y-3 overflow-hidden px-4 py-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className={`flex ${i % 2 === 1 ? "justify-start" : "justify-end"}`}
            >
              <div
                className={`h-16 animate-pulse rounded-lg bg-gray-100 ${
                  i % 2 === 1 ? "w-2/3" : "w-1/2"
                }`}
              />
            </div>
          ))}
        </div>
        {/* Input skeleton */}
        <div className="border-t px-4 py-3">
          <div className="h-10 w-full animate-pulse rounded-lg bg-gray-100" />
        </div>
      </div>
    );
  }

  // ── Session not active banner ─────────────────────────────────
  const isActive = session?.status === "active";

  // ── Render ────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] rounded-lg border bg-white">
      {/* Header */}
      <div className="border-b px-4 py-3">
        <p className="text-sm font-medium text-gray-900">
          {agentLabel(session?.agent_type || "clara")}
        </p>
        <p className="text-xs text-gray-500">
          {session?.title || "Sesión sin título"}
        </p>
      </div>

      {/* Closed session banner */}
      {!isActive && (
        <div className="border-b bg-amber-50 px-4 py-2 text-center">
          <p className="text-xs font-medium text-amber-700">
            Esta sesión está cerrada. No se pueden enviar nuevos mensajes.
          </p>
        </div>
      )}

      {/* Messages error banner */}
      {messagesError && (
        <div className="border-b border-red-200 bg-red-50 px-4 py-3 text-center">
          <p className="text-xs text-red-600">Error al cargar los mensajes</p>
          <button
            onClick={() => refetchMessages()}
            className="mt-1 text-xs text-red-700 underline hover:no-underline"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Stream error banner */}
      {streamError && !messagesError && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-center">
          <p className="text-xs text-amber-700">{streamError}</p>
          {!streamError.startsWith("Reconectando") && (
            <button
              onClick={retryStream}
              className="mt-1 text-xs text-amber-800 underline hover:no-underline"
            >
              Reintentar
            </button>
          )}
        </div>
      )}

      {/* Message area */}
      {!messagesError && messages && messages.length === 0 && !streamingMessage ? (
        <div className="flex flex-1 items-center justify-center px-4">
          <p className="text-sm text-gray-400">
            No hay mensajes todavía. Envía el primero para comenzar.
          </p>
        </div>
      ) : (
        <>
          <MessageList
            messages={messages || []}
            streamingContent={streamingMessage}
          />

          {/* Typing indicator: stream activo pero sin tokens todavía */}
          {isStreaming && !streamingMessage && (
            <div className="flex justify-start px-4 pb-2">
              <div className="max-w-[70%] rounded-lg bg-gray-100 px-4 py-3">
                <div className="flex gap-1.5">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Input */}
      <ChatInput
        onSend={(content) => send(content)}
        disabled={!isActive}
        isStreaming={isStreaming}
      />
    </div>
  );
}
