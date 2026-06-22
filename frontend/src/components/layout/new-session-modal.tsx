"use client";

import { useState } from "react";
import { useCreateSession } from "@/hooks/use-sessions";
import type { AgentType } from "@/lib/types";

interface NewSessionModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (sessionId: number) => void;
}

export default function NewSessionModal({ open, onClose, onCreated }: NewSessionModalProps) {
  const [selectedType, setSelectedType] = useState<AgentType | null>(null);
  const createMutation = useCreateSession();

  const handleCreate = async () => {
    if (!selectedType) return;
    const session = await createMutation.mutateAsync(selectedType);
    setSelectedType(null);
    onCreated(session.id);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-80 rounded-xl bg-white p-6 shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900">Nueva sesión</h3>
        <p className="mt-1 text-sm text-gray-500">
          ¿Qué tipo de sesión quieres crear?
        </p>

        <div className="mt-4 space-y-2">
          <button
            onClick={() => setSelectedType("clara")}
            className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
              selectedType === "clara"
                ? "border-blue-500 bg-blue-50 text-blue-800"
                : "border-gray-200 hover:bg-gray-50 text-gray-700"
            }`}
          >
            <span className="font-medium">Clara</span>
            <span className="block text-xs text-gray-400">Postulación de iniciativa guiada</span>
          </button>

          <button
            onClick={() => setSelectedType("analista_oportunidad")}
            className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
              selectedType === "analista_oportunidad"
                ? "border-blue-500 bg-blue-50 text-blue-800"
                : "border-gray-200 hover:bg-gray-50 text-gray-700"
            }`}
          >
            <span className="font-medium">Analista</span>
            <span className="block text-xs text-gray-400">Análisis de oportunidad económica</span>
          </button>
        </div>

        {createMutation.isError && (
          <p className="mt-3 text-xs text-red-600">
            Error al crear la sesión. Intenta de nuevo.
          </p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100"
            disabled={createMutation.isPending}
          >
            Cancelar
          </button>
          <button
            onClick={handleCreate}
            disabled={!selectedType || createMutation.isPending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {createMutation.isPending ? "Creando..." : "Crear"}
          </button>
        </div>
      </div>
    </div>
  );
}
