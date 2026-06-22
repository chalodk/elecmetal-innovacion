"use client";

import { useParams, useRouter } from "next/navigation";
import { useInitiative } from "@/hooks/use-initiative";
import { StatusBadge, InfoCard, Badge } from "@/components/ui";

export default function InitiativeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const {
    data: initiative,
    isLoading: loading,
    error: loadError,
  } = useInitiative(id);

  if (loading) {
    return (
      <div className="flex items-center justify-center flex-1">
        <p className="text-sm text-gray-400">Cargando iniciativa…</p>
      </div>
    );
  }

  if (loadError || !initiative) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3">
        <p className="text-sm text-red-600">
          {(loadError as Error)?.message || "Iniciativa no encontrada"}
        </p>
        <button
          onClick={() => router.push("/dashboard")}
          className="text-sm text-blue-600 hover:underline"
        >
          Volver al inicio
        </button>
      </div>
    );
  }

  const extra = initiative.dbi_extra as Record<string, unknown> | null;

  return (
    <div className="p-8 max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/dashboard")}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          ← Volver
        </button>
        <h1 className="text-xl font-bold text-gray-900 flex-1">
          {initiative.title}
        </h1>
        <span className="font-mono text-sm text-gray-400">
          {initiative.initiative_code}
        </span>
      </div>

      {/* Status */}
      <div className="flex items-center gap-3">
        <StatusBadge status={initiative.status} />
        <span className="text-sm text-gray-500 capitalize">
          {initiative.initiative_type}
        </span>
        <span className="text-sm text-gray-400">
          Postulada:{" "}
          {initiative.postulation_date
            ? new Date(
                initiative.postulation_date,
              ).toLocaleDateString("es-CL")
            : "—"}
        </span>
      </div>

      {/* Info */}
      <div className="grid grid-cols-2 gap-4">
        <InfoCard title="Problema">
          <p className="text-sm text-gray-700">{initiative.problem}</p>
          {extra?.block_a_extra ? (
            <div className="mt-2 space-y-1 text-xs text-gray-500">
              {(extra.block_a_extra as Record<string, string>).why_it_matters ? (
                <p>
                  <strong>Por que importa:</strong>{" "}
                  {(extra.block_a_extra as Record<string, string>).why_it_matters}
                </p>
              ) : null}
              {(extra.block_a_extra as Record<string, string>).who_has_it ? (
                <p>
                  <strong>Quien lo tiene:</strong>{" "}
                  {(extra.block_a_extra as Record<string, string>).who_has_it}
                </p>
              ) : null}
            </div>
          ) : null}
        </InfoCard>

        <InfoCard title="Solucion">
          <p className="text-sm text-gray-700">{initiative.solution}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge label="TRL" value={initiative.trl} />
            <Badge label="CRL" value={initiative.crl} />
            <Badge label="BRL" value={initiative.brl} />
            <Badge label="Escalabilidad" value={initiative.scalability} />
            {initiative.economic_impact && (
              <Badge label="Impacto" value={initiative.economic_impact} />
            )}
          </div>
        </InfoCard>

        <InfoCard title="Cliente">
          <p className="text-sm text-gray-700">
            <strong>Interno:</strong> {initiative.internal_client || "—"}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Externo:</strong> {initiative.external_client || "—"}
          </p>
        </InfoCard>

        <InfoCard title="Equipo">
          <p className="text-sm text-gray-700">
            <strong>Interno:</strong> {initiative.internal_team || "—"}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Sponsor:</strong> {initiative.sponsor || "—"}
          </p>
          <p className="text-xs text-gray-500">
            Duracion estimada: {initiative.estimated_duration || "—"}
          </p>
        </InfoCard>

        <InfoCard title="Riesgo">
          <p className="text-sm text-gray-700">
            <strong>Duda principal:</strong> {initiative.main_doubt || "—"}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Condicion clave:</strong>{" "}
            {initiative.key_condition || "—"}
          </p>
          <Badge label="Captura de valor" value={initiative.value_capture} />
        </InfoCard>

        <InfoCard title="Hitos">
          <p className="text-xs text-gray-700">
            <strong>Tecnicos:</strong>{" "}
            {initiative.technical_milestones || "—"}
          </p>
          <p className="text-xs text-gray-700">
            <strong>Economicos:</strong>{" "}
            {initiative.financial_milestones || "—"}
          </p>
          <div className="mt-1">
            <Badge
              label="Retorno"
              value={
                initiative.return_horizon
                  ? `${initiative.return_horizon} meses`
                  : "—"
              }
            />
          </div>
        </InfoCard>
      </div>

      {/* DBI original */}
      {initiative.dbi_raw_text && (
        <details className="rounded border bg-white p-3">
          <summary className="text-sm font-medium text-gray-600 cursor-pointer">
            Texto original del DBI
          </summary>
          <pre className="mt-2 text-xs text-gray-500 whitespace-pre-wrap max-h-96 overflow-y-auto">
            {initiative.dbi_raw_text}
          </pre>
        </details>
      )}
    </div>
  );
}
