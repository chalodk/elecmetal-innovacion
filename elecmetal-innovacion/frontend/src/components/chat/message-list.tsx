"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/lib/types";
import MessageBubble from "./message-bubble";

interface MessageListProps {
  messages: Message[];
  /** Contenido del mensaje del asistente que se está streameando */
  streamingContent?: string | null;
}

export default function MessageList({ messages, streamingContent }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll al final cuando llegan nuevos mensajes o tokens
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent]);

  if (messages.length === 0 && !streamingContent) return null;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          role={msg.role}
          content={msg.content}
          created_at={msg.created_at}
        />
      ))}
      {streamingContent && (
        <MessageBubble
          role="assistant"
          content={streamingContent}
          created_at={new Date().toISOString()}
          isStreaming
        />
      )}
      <div ref={bottomRef} />
    </div>
  );
}
