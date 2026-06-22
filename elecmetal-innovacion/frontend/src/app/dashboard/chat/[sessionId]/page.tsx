"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMessages, useSendMessage } from "@/lib/hooks";

interface Message {
  id: number;
  session_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  metadata: unknown;
  created_at: string;
}

interface InitiativeInfo {
  initiative_id: number;
  initiative_code: string;
  status: string;
}

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [input, setInput] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const [initiative, setInitiative] = useState<InitiativeInfo | null>(null);
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  // ── React Query: load messages ───────────────────────────────────────
  const {
    data: apiMessages = [],
    isLoading: loading,
    error: loadError,
  } = useMessages(sessionId);

  // Merge optimistic with real messages (stabilized for useEffect deps)
  const messages = useMemo(
    () => [...apiMessages, ...optimisticMessages],
    [apiMessages, optimisticMessages],
  );

  const sendMessageMutation = useSendMessage(sessionId);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // ── Auto-scroll on new messages / streaming ──────────────────────────
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, scrollToBottom]);

  // ── Send message ─────────────────────────────────────────────────────
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = input.trim();
    if (!content || sendMessageMutation.isPending) return;

    setInput("");
    setStreamingContent("");
    setInitiative(null);

    // Optimistic user message
    const optimisticId = -Date.now();
    const optimisticUser: Message = {
      id: optimisticId,
      session_id: Number(sessionId),
      role: "user",
      content,
      metadata: null,
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages((prev) => [...prev, optimisticUser]);

    try {
      const result = await sendMessageMutation.mutateAsync({
        content,
        onToken: (token) => {
          setStreamingContent((prev) => prev + token);
        },
      });

      // Remove optimistic message on success
      setOptimisticMessages((prev) =>
        prev.filter((m) => m.id !== optimisticId),
      );
      setStreamingContent("");

      // Show initiative info if DBI was persisted
      if (result.initiative) {
        const init = result.initiative as InitiativeInfo;
        if ("initiative_code" in init) {
          setInitiative(init);
        } else if ("parse_error" in result.initiative) {
          // Error handled via mutation state
        }
      }
    } catch {
      // Remove optimistic on error
      setOptimisticMessages((prev) =>
        prev.filter((m) => m.id !== optimisticId),
      );
    }
  };

  const error =
    loadError?.message ||
    (sendMessageMutation.error as Error)?.message ||
    null;

  // ── Render ────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center flex-1">
        <p className="text-sm text-gray-400">Cargando conversacion…</p>
      </div>
    );
  }

  if (error && messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3">
        <p className="text-sm text-red-600">Error al cargar la sesion</p>
        <p className="text-xs text-gray-400">{error}</p>
        <button
          onClick={() => router.push("/dashboard")}
          className="text-sm text-blue-600 hover:underline"
        >
          Volver al inicio
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 px-8">
      {/* Header */}
      <div className="flex items-center gap-3 pb-4 border-b mb-4">
        <button
          onClick={() => router.push("/dashboard")}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          ← Volver
        </button>
        <h1 className="text-sm font-medium text-gray-700 truncate">
          Sesion {sessionId}
        </h1>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pb-4">
        {messages.length === 0 && !streamingContent && (
          <p className="text-center text-sm text-gray-400 pt-8">
            Envia tu primer mensaje para comenzar.
          </p>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-white border text-gray-800"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Streaming token display */}
        {streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[75%] bg-white border rounded-lg px-4 py-2 text-sm text-gray-800 whitespace-pre-wrap">
              {streamingContent}
              <span className="inline-block w-2 h-4 bg-gray-400 ml-0.5 animate-pulse" />
            </div>
          </div>
        )}

        {/* Typing indicator (before first token arrives) */}
        {sendMessageMutation.isPending && !streamingContent && (
          <div className="flex justify-start">
            <div className="bg-white border rounded-lg px-4 py-2 text-sm text-gray-400 animate-pulse">
              Clara esta escribiendo…
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Initiative persisted banner */}
      {initiative && (
        <div className="mb-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3">
          <p className="text-sm font-medium text-green-800">
            ✅ Iniciativa registrada
          </p>
          <p className="text-xs text-green-700 mt-1">
            Codigo:{" "}
            <span className="font-mono font-semibold">
              {initiative.initiative_code}
            </span>
          </p>
          <button
            onClick={() =>
              router.push(`/dashboard/initiatives/${initiative.initiative_id}`)
            }
            className="mt-1 text-xs text-blue-600 hover:underline"
          >
            Ver iniciativa →
          </button>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="mb-2 rounded bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSend} className="flex gap-2 pt-2 border-t">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu mensaje…"
          disabled={sendMessageMutation.isPending}
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || sendMessageMutation.isPending}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
