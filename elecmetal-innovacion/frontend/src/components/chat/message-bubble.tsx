import type { MessageRole } from "@/lib/types";

interface MessageBubbleProps {
  role: MessageRole;
  content: string;
  created_at: string;
  /** Si es true, muestra un cursor parpadeante al final del contenido */
  isStreaming?: boolean;
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" });
}

export default function MessageBubble({ role, content, created_at, isStreaming = false }: MessageBubbleProps) {
  if (role === "system") return null;

  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-2.5 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm">
          {content}
          {isStreaming && (
            <span className="inline-block w-[2px] h-[1em] ml-0.5 align-text-bottom bg-current animate-blink" />
          )}
        </p>
        <p
          className={`mt-1 text-xs ${
            isUser ? "text-blue-200" : "text-gray-400"
          }`}
        >
          {isStreaming ? "Escribiendo..." : formatTime(created_at)}
        </p>
      </div>
    </div>
  );
}
