"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useInitiative } from "@/hooks/use-initiative";
import {
  useTriggerEvaluation,
  useEvaluationByInitiative,
  useReviewEvaluation,
} from "@/hooks/use-evaluation";
import StatusBadge from "@/components/ui/StatusBadge";
import { ScoreBox } from "@/components/ui";
import DbiBlockSection from "@/components/panel-directora/dbi-block-section";

interface EvaluationData {
  id: number;
  initiative_id: number;
  status: string;
  results: {
    scores: Record<
      string,
      Record<string, { score: number; evidence: string }>
    >;
    derived: {
      novedad: number;
      indice_incertidumbre: number;
      puntaje_total: number;
      puntaje_normalizado: number;
      compuerta_sandbox: string;
      compuerta_innovacion: string;
      resumen: string;
      recomendacion: string;
    };
  } | null;
  veredicto: string | null;
  reviewed_at: string | null;
  created_at: string;
}

const DIMENSION_LABELS: Record<string, string> = {
  problema: "Problema",
  solucion: "Solucion",
  cliente: "Cliente",
  alineamiento: "Alineamiento",
  equipo: "Equipo y recursos",
  riesgo: "Riesgo e incertidumbre",
  hitos: "Hitos",
};

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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("es-CL", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function InitiativeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const {
    data: initiative,
    isLoading,
    isError,
    refetch,
  } = useInitiative(id);

  const { data: evaluation } = useEvaluationByInitiative(id);
  const activateEvaluator = useTriggerEvaluation();
  const reviewEval = useReviewEvaluation();

  const [veredicto, setVeredicto] = useState("");

  const error =
    (activateEvaluator.error as Error)?.message ||
    (reviewEval.error as Error)?.message ||
    null;

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

  // Error / not found
  if (isError || !initiative) {
    return (
      <div className="space-y-4">
        <Link
          href="/dashboard/admin"
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

  const evalData = evaluation as EvaluationData | null;

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
        { label: "Alineamiento estratégico", value: initiative.strategic_alignment },
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
        { label: "Hitos financieros", value: initiative.financial_milestones },
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
      {/* Back link + Actions */}
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard/admin"
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          ← Volver a la lista
        </Link>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {initiative.status === "notificado" && (
            <button
              onClick={() => activateEvaluator.mutate(initiative.id)}
              disabled={activateEvaluator.isPending}
              className="px-3 py-1.5 text-sm font-medium rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200 disabled:opacity-50"
            >
              {activateEvaluator.isPending ? "Procesando…" : "Enviar a evaluacion"}
            </button>
          )}
          {initiative.status === "en_evaluacion" && (
            <button
              onClick={() => activateEvaluator.mutate(initiative.id)}
              disabled={activateEvaluator.isPending}
              className="px-3 py-1.5 text-sm font-medium rounded bg-purple-100 text-purple-700 hover:bg-purple-200 disabled:opacity-50"
            >
              {activateEvaluator.isPending ? "Evaluando…" : "Activar Evaluador IA"}
            </button>
          )}
        </div>
      </div>

      {/* Header */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-gray-400">
                {initiative.initiative_code}
              </span>
              <StatusBadge status={initiative.status} />
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

      {/* Error */}
      {error && (
        <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

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

      {/* Evaluation Results */}
      {evalData?.results && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-gray-900 pt-4 border-t">
            Resultados del Evaluador
          </h2>

          <div className="grid grid-cols-4 gap-3">
            <ScoreBox
              label="Puntaje Total"
              value={evalData.results.derived.puntaje_total}
              max={110}
            />
            <ScoreBox
              label="Normalizado"
              value={evalData.results.derived.puntaje_normalizado}
              max={100}
            />
            <ScoreBox
              label="Novedad"
              value={evalData.results.derived.novedad}
              max={5}
            />
            <ScoreBox
              label="Incertidumbre"
              value={evalData.results.derived.indice_incertidumbre}
              max={5}
              precision={1}
            />
          </div>

          <div className="flex gap-3 text-sm">
            <span className="px-3 py-1 rounded bg-gray-100 text-gray-700">
              Sandbox: {evalData.results.derived.compuerta_sandbox}
            </span>
            <span className="px-3 py-1 rounded bg-gray-100 text-gray-700">
              Innovacion: {evalData.results.derived.compuerta_innovacion}
            </span>
          </div>

          {Object.entries(evalData.results.scores).map(([dim, items]) => (
            <div key={dim} className="rounded border bg-white p-3">
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                {DIMENSION_LABELS[dim] || dim}
              </h3>
              <div className="space-y-1">
                {Object.entries(items).map(([key, item]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between gap-3 text-xs"
                  >
                    <span className="text-gray-600 flex-1">
                      {key.replace(/_/g, " ")}:{" "}
                      <span className="text-gray-400 italic">
                        {item.evidence?.slice(0, 80)}
                        {(item.evidence?.length || 0) > 80 ? "…" : ""}
                      </span>
                    </span>
                    <span
                      className={`inline-block w-6 h-6 rounded text-center leading-6 font-bold text-xs ${
                        item.score === 5
                          ? "bg-green-100 text-green-700"
                          : item.score === 3
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-red-100 text-red-700"
                      }`}
                    >
                      {item.score}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="rounded border bg-white p-4 space-y-2">
            <p className="text-sm text-gray-700">
              <strong>Resumen:</strong> {evalData.results.derived.resumen}
            </p>
            <p className="text-sm text-gray-700">
              <strong>Recomendacion:</strong>{" "}
              {evalData.results.derived.recomendacion}
            </p>
          </div>

          {/* Veredicto */}
          <div className="rounded border bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">
              Registrar Veredicto del Comite
            </h3>
            {evalData.veredicto ? (
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">Veredicto actual:</span>
                <StatusBadge status={evalData.veredicto} />
                {evalData.reviewed_at && (
                  <span className="text-xs text-gray-400">
                    Validado: {new Date(evalData.reviewed_at).toLocaleDateString("es-CL")}
                  </span>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <select
                  value={veredicto}
                  onChange={(e) => setVeredicto(e.target.value)}
                  className="rounded border px-3 py-1.5 text-sm"
                >
                  <option value="">Seleccionar…</option>
                  <option value="aprobada">Aprobada</option>
                  <option value="rechazada">Rechazada</option>
                  <option value="pendiente">Pendiente</option>
                </select>
                <button
                  onClick={() =>
                    reviewEval.mutate({
                      evaluationId: String(evalData.id),
                      veredicto,
                      validate: true,
                    })
                  }
                  disabled={!veredicto || reviewEval.isPending}
                  className="px-3 py-1.5 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {reviewEval.isPending ? "Guardando…" : "Registrar y validar"}
                </button>
              </div>
            )}
          </div>
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
