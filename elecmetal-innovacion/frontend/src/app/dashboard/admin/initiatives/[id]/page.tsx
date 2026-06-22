"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  useInitiative,
  useTriggerEvaluation,
  useEvaluationByInitiative,
  useReviewEvaluation,
} from "@/lib/hooks";
import { InfoCard, Badge, ScoreBox } from "@/components/ui";

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

const STATUS_LABELS: Record<string, string> = {
  persistido: "Persistido",
  notificado: "Notificado",
  en_evaluacion: "En evaluacion",
  evaluado: "Evaluado",
  validado: "Validado",
};

const DIMENSION_LABELS: Record<string, string> = {
  problema: "Problema",
  solucion: "Solucion",
  cliente: "Cliente",
  alineamiento: "Alineamiento",
  equipo: "Equipo y recursos",
  riesgo: "Riesgo e incertidumbre",
  hitos: "Hitos",
};

export default function InitiativeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: initiative,
    isLoading: loading,
    error: loadError,
  } = useInitiative(id);

  const { data: evaluation } = useEvaluationByInitiative(id);
  const activateEvaluator = useTriggerEvaluation();
  const reviewEval = useReviewEvaluation();

  const [veredicto, setVeredicto] = useState("");

  const error =
    (loadError as Error)?.message ||
    (activateEvaluator.error as Error)?.message ||
    (reviewEval.error as Error)?.message ||
    null;

  if (loading) {
    return (
      <div className="flex items-center justify-center flex-1">
        <p className="text-sm text-gray-400">Cargando iniciativa…</p>
      </div>
    );
  }

  if (!initiative) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3">
        <p className="text-sm text-red-600">Iniciativa no encontrada</p>
        <button
          onClick={() => router.push("/dashboard/admin")}
          className="text-sm text-blue-600 hover:underline"
        >
          Volver al panel
        </button>
      </div>
    );
  }

  const extra = initiative.dbi_extra as Record<string, unknown> | null;
  const evalData = evaluation as EvaluationData | null;

  return (
    <div className="p-6 space-y-4 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/dashboard/admin")}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          ← Panel
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
        <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700">
          {STATUS_LABELS[initiative.status] || initiative.status}
        </span>
        <span className="text-sm text-gray-500 capitalize">
          {initiative.initiative_type}
        </span>
        <span className="text-sm text-gray-400">
          {initiative.applicant_name} · {initiative.area}
        </span>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        {initiative.status === "notificado" && (
          <button
            onClick={() => activateEvaluator.mutate(id)}
            disabled={activateEvaluator.isPending}
            className="px-3 py-1.5 text-sm font-medium rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200 disabled:opacity-50"
          >
            {activateEvaluator.isPending
              ? "Procesando…"
              : "Enviar a evaluacion"}
          </button>
        )}
        {initiative.status === "en_evaluacion" && (
          <button
            onClick={() => activateEvaluator.mutate(id)}
            disabled={activateEvaluator.isPending}
            className="px-3 py-1.5 text-sm font-medium rounded bg-purple-100 text-purple-700 hover:bg-purple-200 disabled:opacity-50"
          >
            {activateEvaluator.isPending
              ? "Evaluando…"
              : "Activar Evaluador IA"}
          </button>
        )}
      </div>

      {/* DBI Core Info */}
      <div className="grid grid-cols-2 gap-4">
        <InfoCard title="Problema (Bloque A)">
          <p className="text-sm text-gray-700">{initiative.problem}</p>
          {extra && (
            <div className="mt-2 space-y-1 text-xs text-gray-500">
              {(extra.block_a_extra as Record<string, string>)
                ?.why_it_matters && (
                <p>
                  <strong>Por que importa:</strong>{" "}
                  {(extra.block_a_extra as Record<string, string>).why_it_matters}
                </p>
              )}
              {(extra.block_a_extra as Record<string, string>)?.who_has_it && (
                <p>
                  <strong>Quien lo tiene:</strong>{" "}
                  {(extra.block_a_extra as Record<string, string>).who_has_it}
                </p>
              )}
            </div>
          )}
        </InfoCard>

        <InfoCard title="Solucion (Bloque B)">
          <p className="text-sm text-gray-700">{initiative.solution}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <Badge label="TRL" value={initiative.trl} />
            <Badge label="Escalabilidad" value={initiative.scalability} />
            {initiative.economic_impact && (
              <Badge label="Impacto" value={initiative.economic_impact} />
            )}
          </div>
          {extra && (
            <div className="mt-2 space-y-1 text-xs text-gray-500">
              {(extra.block_b_extra as Record<string, string>)
                ?.differentiator_novelty_grade && (
                <p>
                  <strong>Novedad:</strong>{" "}
                  {(extra.block_b_extra as Record<string, string>).differentiator_novelty_grade}
                </p>
              )}
              {(extra.block_b_extra as Record<string, string>)
                ?.trl_evidence && (
                <p>
                  <strong>Evidencia TRL:</strong>{" "}
                  {(extra.block_b_extra as Record<string, string>).trl_evidence}
                </p>
              )}
            </div>
          )}
        </InfoCard>

        <InfoCard title="Cliente (Bloque C)">
          <p className="text-sm text-gray-700">
            Interno: {initiative.internal_client || "—"}
          </p>
          <p className="text-sm text-gray-700">
            Externo: {initiative.external_client || "—"}
          </p>
          <div className="mt-2">
            <Badge label="CRL" value={initiative.crl} />
          </div>
        </InfoCard>

        <InfoCard title="Equipo (Bloque E)">
          <p className="text-sm text-gray-700">
            <strong>Interno:</strong> {initiative.internal_team || "—"}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Sponsor:</strong> {initiative.sponsor || "—"}
          </p>
          <p className="text-xs text-gray-500">
            Duracion: {initiative.estimated_duration || "—"}
          </p>
        </InfoCard>

        <InfoCard title="Riesgo (Bloque F)">
          <p className="text-sm text-gray-700">
            <strong>Duda:</strong> {initiative.main_doubt || "—"}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Condicion:</strong> {initiative.key_condition || "—"}
          </p>
          <div className="mt-2">
            <Badge label="BRL" value={initiative.brl} />
            <span className="ml-2 text-xs text-gray-500">
              Captura: {initiative.value_capture || "—"}
            </span>
          </div>
        </InfoCard>

        <InfoCard title="Hitos (Bloque G)">
          <p className="text-sm text-gray-700">
            <strong>Tecnicos:</strong>{" "}
            {initiative.technical_milestones || "—"}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Economicos:</strong>{" "}
            {initiative.financial_milestones || "—"}
          </p>
          <div className="mt-2">
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
                <span className="text-sm text-gray-600">
                  Veredicto actual:
                </span>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    evalData.veredicto === "aprobada"
                      ? "bg-green-100 text-green-700"
                      : evalData.veredicto === "rechazada"
                        ? "bg-red-100 text-red-700"
                        : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {evalData.veredicto}
                </span>
                {evalData.reviewed_at && (
                  <span className="text-xs text-gray-400">
                    Validado:{" "}
                    {new Date(evalData.reviewed_at).toLocaleDateString(
                      "es-CL",
                    )}
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

      {/* Error */}
      {error && (
        <div className="rounded bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Raw DBI text */}
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
