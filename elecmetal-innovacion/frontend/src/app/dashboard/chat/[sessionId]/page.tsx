"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { getMessages, sendMessage, type SSEEvent } from "@/lib/api";

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

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");
  const [initiative, setInitiative] = useState<InitiativeInfo | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // ── Load messages on mount ──────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) {
          router.push("/login");
          return;
        }
        const msgs = await getMessages(session.access_token, sessionId);
        if (!cancelled) setMessages(msgs);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId, router]);

  // ── Auto-scroll ──────────────────────────────────────────────────────

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, scrollToBottom]);

  // ── Send message ─────────────────────────────────────────────────────

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = input.trim();
    if (!content || sending) return;

    setInput("");
    setSending(true);
    setError(null);
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
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.push("/login");
        return;
      }

      // Use SSE-capable sendMessage with streaming tokens
      const result = await sendMessage(
        session.access_token,
        sessionId,
        content,
        (token) => {
          setStreamingContent((prev) => prev + token);
        },
      );

      // Remove optimistic + add real user message + assistant
      setStreamingContent("");
      setMessages((prev) => {
        const withoutOptimistic = prev.filter((m) => m.id !== optimisticId);
        const userMsg: Message = {
          id: optimisticId - 1,
          session_id: Number(sessionId),
          role: "user",
          content,
          metadata: null,
          created_at: new Date().toISOString(),
        };
        const asstMsg: Message = {
          id: result.message_id,
          session_id: Number(sessionId),
          role: "assistant",
          content: result.content,
          metadata: null,
          created_at: new Date().toISOString(),
        };
        return [...withoutOptimistic, userMsg, asstMsg];
      });

      // Show initiative info if DBI was persisted
      if (result.initiative) {
        const init = result.initiative as InitiativeInfo;
        if ("initiative_code" in init) {
          setInitiative(init as InitiativeInfo);
        } else if ("parse_error" in result.initiative) {
          setError(
            `Error al parsear el DBI: ${(result.initiative as { parse_error: string }).parse_error}`,
          );
        } else if ("persistence_error" in result.initiative) {
          setError(
            `Error al guardar la iniciativa: ${(result.initiative as { persistence_error: string }).persistence_error}`,
          );
        }
      }
    } catch (e) {
      setError((e as Error).message);
      setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
    } finally {
      setSending(false);
    }
  };

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
        {sending && !streamingContent && (
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
          disabled={sending}
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || sending}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
