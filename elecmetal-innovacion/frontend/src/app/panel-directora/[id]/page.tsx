"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useInitiative } from "@/hooks/use-initiative";
import InitiativeStatusBadge from "@/components/panel-directora/initiative-status-badge";
import DbiBlockSection from "@/components/panel-directora/dbi-block-section";

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  return date.toLocaleDateString("es-CL", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

const TYPE_LABELS: Record<string, string> = {
  interna: "Interna",
  externa: "Externa",
  mixta: "Mixta",
};

const SCALABILITY_LABELS: Record<string, string> = {
  Local: "Local",
  Interna: "Interna",
  Externa: "Externa",
};

const VEREDICTO_LABELS: Record<string, { label: string; className: string }> = {
  aprobada: {
    label: "Aprobada",
    className: "bg-green-100 text-green-700 border-green-300",
  },
  rechazada: {
    label: "Rechazada",
    className: "bg-red-100 text-red-700 border-red-300",
  },
  pendiente: {
    label: "Pendiente",
    className: "bg-gray-100 text-gray-700 border-gray-300",
  },
};

export default function InitiativeDetailPage() {
  const params = useParams();
  const id = Number(params.id);

  const { data: initiative, isLoading, isError, refetch } = useInitiative(id);

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-64 rounded bg-gray-200" />
        <div className="h-4 w-48 rounded bg-gray-200" />
        <div className="mt-6 space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 rounded-lg bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  // Error
  if (isError || !initiative) {
    return (
      <div className="space-y-4">
        <Link
          href="/panel-directora"
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          ← Volver a la lista
        </Link>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-red-700">
            Error al cargar la iniciativa.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-2 text-sm font-medium text-red-600 underline hover:text-red-800"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // Build DBI block sections
  const blocks = [
    {
      letter: "A",
      title: "Problema",
      fields: [
        { label: "Problema", value: initiative.problem },
        { label: "Área", value: initiative.area },
      ],
      defaultOpen: true,
    },
    {
      letter: "B",
      title: "Solución",
      fields: [
        { label: "Solución propuesta", value: initiative.solution },
        { label: "Impacto económico", value: initiative.economic_impact },
        {
          label: "TRL (Technology Readiness Level)",
          value: initiative.trl ? `Nivel ${initiative.trl}/9` : null,
        },
        {
          label: "Escalabilidad",
          value: initiative.scalability
            ? SCALABILITY_LABELS[initiative.scalability] ?? initiative.scalability
            : null,
        },
      ],
    },
    {
      letter: "C",
      title: "Cliente",
      fields: [
        { label: "Cliente interno", value: initiative.internal_client },
        { label: "Cliente externo", value: initiative.external_client },
        {
          label: "CRL (Customer Readiness Level)",
          value: initiative.crl ? `Nivel ${initiative.crl}/9` : null,
        },
      ],
    },
    {
      letter: "D",
      title: "Alineamiento Estratégico",
      fields: [
        {
          label: "Alineamiento estratégico",
          value: initiative.strategic_alignment,
        },
      ],
    },
    {
      letter: "E",
      title: "Equipo y Recursos",
      fields: [
        { label: "Patrocinador", value: initiative.sponsor },
        { label: "Equipo interno", value: initiative.internal_team },
        { label: "Equipo externo", value: initiative.external_team },
        { label: "Duración estimada", value: initiative.estimated_duration },
      ],
    },
    {
      letter: "F",
      title: "Riesgo e Incertidumbre",
      fields: [
        { label: "Duda principal", value: initiative.main_doubt },
        { label: "Condición clave", value: initiative.key_condition },
        { label: "Captura de valor", value: initiative.value_capture },
        {
          label: "BRL (Business Readiness Level)",
          value: initiative.brl ? `Nivel ${initiative.brl}/9` : null,
        },
      ],
    },
    {
      letter: "G",
      title: "Hitos",
      fields: [
        { label: "Hitos técnicos", value: initiative.technical_milestones },
        {
          label: "Hitos financieros",
          value: initiative.financial_milestones,
        },
        {
          label: "Horizonte de retorno",
          value: initiative.return_horizon
            ? `${initiative.return_horizon} meses`
            : null,
        },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        href="/panel-directora"
        className="text-sm text-blue-600 hover:text-blue-800"
      >
        ← Volver a la lista
      </Link>

      {/* Header */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-gray-400">
                {initiative.initiative_code}
              </span>
              <InitiativeStatusBadge status={initiative.status} />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">
              {initiative.title}
            </h1>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500">
              <span>{initiative.applicant_name}</span>
              <span>·</span>
              <span>{initiative.area}</span>
              <span>·</span>
              <span>{formatDate(initiative.postulation_date)}</span>
              <span>·</span>
              <span>{TYPE_LABELS[initiative.initiative_type] ?? initiative.initiative_type}</span>
            </div>
          </div>
        </div>
      </div>

      {/* DBI Blocks */}
      <div className="space-y-3">
        {blocks.map((block) => (
          <DbiBlockSection
            key={block.letter}
            letter={block.letter}
            title={block.title}
            fields={block.fields}
            defaultOpen={block.defaultOpen}
          />
        ))}
      </div>

      {/* Evaluation (if exists) */}
      {initiative.evaluation && (
        <div className="rounded-lg border border-purple-200 bg-purple-50 p-6">
          <h3 className="text-sm font-semibold text-purple-900">
            Evaluación
          </h3>
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-purple-600">Estado:</span>
              <span className="rounded-full bg-purple-200 px-2 py-0.5 text-xs font-medium text-purple-800">
                {initiative.evaluation.status}
              </span>
            </div>

            {initiative.evaluation.veredicto && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-purple-600">Veredicto:</span>
                {(() => {
                  const v = VEREDICTO_LABELS[initiative.evaluation.veredicto];
                  if (!v) return <span className="text-xs text-gray-600">{initiative.evaluation.veredicto}</span>;
                  return (
                    <span
                      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${v.className}`}
                    >
                      {v.label}
                    </span>
                  );
                })()}
              </div>
            )}

            {initiative.evaluation.reviewed_at && (
              <p className="text-xs text-purple-500">
                Revisado: {formatDate(initiative.evaluation.reviewed_at)}
              </p>
            )}
          </div>

          {initiative.evaluation.results && (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-purple-700 hover:text-purple-900">
                Ver resultados completos (JSON)
              </summary>
              <pre className="mt-2 overflow-auto rounded bg-purple-100 p-3 text-xs text-purple-900">
                {JSON.stringify(initiative.evaluation.results, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}

      {/* DBI Raw Text (collapsible) */}
      {initiative.dbi_raw_text && (
        <details className="rounded-lg border border-gray-200 bg-white p-4">
          <summary className="cursor-pointer text-xs font-medium text-gray-500 hover:text-gray-700">
            Ver texto original del DBI
          </summary>
          <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-xs text-gray-600">
            {initiative.dbi_raw_text}
          </pre>
        </details>
      )}
    </div>
  );
}
