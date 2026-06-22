"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useSessions } from "@/hooks/use-sessions";
import { signOut } from "@/app/dashboard/actions";
import SessionItem from "./session-item";
import NewSessionModal from "./new-session-modal";

interface SidebarProps {
  user: { email: string | null; role: string | null };
}

export default function Sidebar({ user }: SidebarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedSessionId = searchParams.get("session_id")
    ? Number(searchParams.get("session_id"))
    : null;

  const { data: sessions, isLoading, isError, refetch } = useSessions();
  const [modalOpen, setModalOpen] = useState(false);

  const handleSelectSession = (id: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("session_id", String(id));
    router.push(`/dashboard?${params.toString()}`);
  };

  const handleSessionCreated = (id: number) => {
    handleSelectSession(id);
  };

  return (
    <>
      <aside className="flex w-64 flex-col border-r bg-white">
        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <span className="text-lg font-bold text-gray-900">Elecmetal</span>
        </div>

        {/* New session button */}
        <div className="px-3 pb-2">
          <button
            onClick={() => setModalOpen(true)}
            className="flex w-full items-center justify-center gap-1 rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-500 hover:border-gray-400 hover:text-gray-700 transition-colors"
          >
            <span className="text-lg leading-none">+</span>
            Nueva sesión
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-3">
          <p className="mb-2 text-xs font-semibold uppercase text-gray-400">
            Sesiones
          </p>

          {/* Loading */}
          {isLoading && (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse rounded-lg bg-gray-100 px-3 py-3">
                  <div className="h-3 w-16 rounded bg-gray-200" />
                  <div className="mt-2 h-2.5 w-24 rounded bg-gray-200" />
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {isError && !isLoading && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-center">
              <p className="text-xs text-red-600">Error al cargar sesiones</p>
              <button
                onClick={() => refetch()}
                className="mt-1 text-xs text-red-700 underline hover:no-underline"
              >
                Reintentar
              </button>
            </div>
          )}

          {/* Empty */}
          {!isLoading && !isError && sessions?.length === 0 && (
            <div className="rounded-lg bg-gray-50 p-4 text-center">
              <p className="text-xs text-gray-500">
                No hay sesiones todavía. Crea la primera para comenzar.
              </p>
            </div>
          )}

          {/* Sessions list */}
          {!isLoading && !isError && sessions && sessions.length > 0 && (
            <div className="space-y-1">
              {sessions.map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={session.id === selectedSessionId}
                  onSelect={handleSelectSession}
                />
              ))}
            </div>
          )}
        </div>

        {/* Admin link — solo directora/admin */}
        {user.role && (user.role === "directora" || user.role === "admin") && (
          <div className="border-t px-3 py-2">
            <button
              onClick={() => router.push("/panel-directora")}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-purple-700 hover:bg-purple-50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Panel Directora
            </button>
          </div>
        )}

        {/* User footer */}
        <div className="border-t px-4 py-3">
          <p className="truncate text-xs text-gray-500">{user.email}</p>
          <form action={signOut}>
            <button
              type="submit"
              className="mt-1 text-xs text-red-600 hover:underline"
            >
              Cerrar sesión
            </button>
          </form>
        </div>
      </aside>

      <NewSessionModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={handleSessionCreated}
      />
    </>
  );
}
