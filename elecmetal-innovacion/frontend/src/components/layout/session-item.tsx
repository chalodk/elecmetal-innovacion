"use client";

import type { Session } from "@/lib/types";

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  onSelect: (id: number) => void;
}

function agentLabel(type: string): string {
  return type === "clara" ? "Clara" : "Analista";
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) {
    return date.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" });
  }
  if (days === 1) return "Ayer";
  if (days < 7) return `Hace ${days} días`;
  return date.toLocaleDateString("es-CL", { day: "numeric", month: "short" });
}

export default function SessionItem({ session, isActive, onSelect }: SessionItemProps) {
  return (
    <button
      onClick={() => onSelect(session.id)}
      className={`w-full rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
        isActive
          ? "bg-blue-50 text-blue-800 border border-blue-200"
          : "text-gray-700 hover:bg-gray-100 border border-transparent"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex h-2 w-2 rounded-full ${
            session.status === "active" ? "bg-green-400" : "bg-gray-300"
          }`}
        />
        <span className="font-medium">
          {agentLabel(session.agent_type)}
        </span>
        <span className="ml-auto text-xs text-gray-400">
          {formatDate(session.created_at)}
        </span>
      </div>
      <p className="mt-0.5 truncate text-xs text-gray-500">
        {session.title || "Sesión sin título"}
      </p>
    </button>
  );
}
