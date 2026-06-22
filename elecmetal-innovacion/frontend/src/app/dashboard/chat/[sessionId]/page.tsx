"use client";

import { useParams } from "next/navigation";
import ChatView from "@/components/chat/chat-view";

export default function ChatPage() {
  const params = useParams();
  const sessionId = Number(params.sessionId);

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center flex-1">
        <p className="text-sm text-gray-400">Sesión no encontrada</p>
      </div>
    );
  }

  return <ChatView sessionId={sessionId} />;
}
