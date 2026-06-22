"use client";

import { useState, type FormEvent } from "react";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  /** Si el chat está streameando la respuesta del asistente */
  isStreaming?: boolean;
}

export default function ChatInput({ onSend, disabled = false, isStreaming = false }: ChatInputProps) {
  const [value, setValue] = useState("");

  const trimmed = value.trim();
  const canSend = trimmed.length > 0 && !disabled && !isStreaming;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSend) return;
    onSend(trimmed);
    setValue("");
  }

  const placeholder = isStreaming
    ? "Clara está escribiendo..."
    : "Escribe tu mensaje...";

  const buttonLabel = isStreaming
    ? "Enviando..."
    : disabled
      ? "Enviando..."
      : "Enviar";

  return (
    <form onSubmit={handleSubmit} className="border-t bg-white px-4 py-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          disabled={disabled || isStreaming}
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          type="submit"
          disabled={!canSend}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 transition-colors"
        >
          {buttonLabel}
        </button>
      </div>
    </form>
  );
}
