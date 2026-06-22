"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useInitiatives } from "@/hooks/use-initiatives";
import InitiativeCard from "@/components/panel-directora/initiative-card";
import type { InitiativeStatus } from "@/lib/types";

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Todas" },
  { value: "dbi_generado", label: "DBI Generado" },
  { value: "persistido", label: "Persistido" },
  { value: "notificado", label: "Notificado" },
  { value: "en_evaluacion", label: "En Evaluación" },
  { value: "evaluado", label: "Evaluado" },
  { value: "validado", label: "Validado" },
  { value: "veredicto", label: "Veredicto" },
];

export default function PanelDirectoraPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<string>("");

  const { data, isLoading, isError, refetch } = useInitiatives(
    statusFilter
      ? { status: statusFilter as InitiativeStatus, limit: 50 }
      : { limit: 50 },
  );

  return (
    <div className="space-y-6">
      {/* Header + Filter */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Iniciativas</h2>
          <p className="mt-1 text-sm text-gray-500">
            Revisa y gestiona las postulaciones de innovación.
          </p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="animate-pulse rounded-lg border border-gray-200 bg-white p-4"
            >
              <div className="h-3 w-24 rounded bg-gray-200" />
              <div className="mt-2 h-4 w-3/4 rounded bg-gray-200" />
              <div className="mt-2 h-3 w-1/2 rounded bg-gray-100" />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-red-700">
            Error al cargar las iniciativas.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-2 text-sm font-medium text-red-600 underline hover:text-red-800"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && (!data?.data || data.data.length === 0) && (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm font-medium text-gray-500">
            {statusFilter
              ? `No hay iniciativas en estado "${STATUS_OPTIONS.find((o) => o.value === statusFilter)?.label}".`
              : "No hay iniciativas para revisar."}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Cuando los postulantes completen su DBI con Clara, aparecerán aquí.
          </p>
        </div>
      )}

      {/* List */}
      {!isLoading && !isError && data?.data && data.data.length > 0 && (
        <>
          <div className="space-y-3">
            {data.data.map((initiative) => (
              <InitiativeCard
                key={initiative.id}
                initiative={initiative}
                onClick={(id) => router.push(`/panel-directora/${id}`)}
              />
            ))}
          </div>

          {data.pagination.has_more && (
            <p className="text-center text-xs text-gray-400">
              Mostrando las últimas {data.data.length} iniciativas. Usa los
              filtros para encontrar más.
            </p>
          )}
        </>
      )}
    </div>
  );
}
