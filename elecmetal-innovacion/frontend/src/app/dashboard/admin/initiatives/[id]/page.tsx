"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  getInitiative,
  triggerEvaluation,
  getEvaluationByInitiative,
  reviewEvaluation,
} from "@/lib/api";
import { StatusBadge, InfoCard, Badge, ScoreBox } from "@/components/ui";

interface InitiativeDetail {
  id: number;
  initiative_code: string;
  title: string;
  status: string;
  initiative_type: string;
  area: string;
  applicant_name: string;
  problem: string;
  solution: string;
  economic_impact: string;
  trl: number | null;
  crl: number | null;
  brl: number | null;
  scalability: string;
  internal_client: string;
  external_client: string;
  sponsor: string;
  internal_team: string;
  external_team: string;
  estimated_duration: string;
  main_doubt: string;
  key_condition: string;
  value_capture: string;
  technical_milestones: string;
  financial_milestones: string;
  return_horizon: number | null;
  strategic_alignment: string;
  dbi_raw_text: string;
  dbi_extra: Record<string, unknown> | null;
  postulation_date: string;
  created_at: string;
  updated_at: string;
}

interface EvaluationData {
  id: number;
  initiative_id: number;
  status: string;
  results: {
    scores: Record<string, Record<string, { score: number; evidence: string }>>;
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
  reviewed_by: string | null;
  reviewed_at: string | null;
  veredicto: string | null;
  created_at: string;
  updated_at: string;
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

  const [initiative, setInitiative] = useState<InitiativeDetail | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [veredicto, setVeredicto] = useState<string>("");

  const supabase = createClient();

  const load = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push("/login"); return; }

      const init = await getInitiative(session.access_token, id);
      setInitiative(init);

      // Load evaluation via the new initiative-scoped endpoint
      try {
        const evalData = await getEvaluationByInitiative(
          session.access_token,
          id,
        );
        setEvaluation(evalData);
      } catch {
        // No evaluation yet — that's fine
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleTriggerEvaluator = async () => {
    if (!initiative) return;
    setActionLoading(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
      await triggerEvaluation(session.access_token, String(initiative.id));
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleVeredicto = async () => {
    if (!evaluation || !veredicto) return;
    setActionLoading(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
      await reviewEvaluation(session.access_token, String(evaluation.id), {
        veredicto,
        validate: true,
      });
      await load();
      setVeredicto("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionLoading(false);
    }
  };

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

      {/* Status + Type */}
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
            onClick={handleTriggerEvaluator}
            disabled={actionLoading}
            className="px-3 py-1.5 text-sm font-medium rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200 disabled:opacity-50"
          >
            {actionLoading ? "Procesando…" : "Enviar a evaluacion"}
          </button>
        )}
        {initiative.status === "en_evaluacion" && (
          <button
            onClick={handleTriggerEvaluator}
            disabled={actionLoading}
            className="px-3 py-1.5 text-sm font-medium rounded bg-purple-100 text-purple-700 hover:bg-purple-200 disabled:opacity-50"
          >
            {actionLoading ? "Evaluando…" : "Activar Evaluador IA"}
          </button>
        )}
      </div>

      {/* DBI Core Info */}
      <div className="grid grid-cols-2 gap-4">
        <InfoCard title="Problema (Bloque A)">
          <p className="text-sm text-gray-700">{initiative.problem}</p>
          {extra && (
            <div className="mt-2 space-y-1 text-xs text-gray-500">
              {(extra.block_a_extra as Record<string, string>)?.why_it_matters && (
                <p><strong>Por que importa:</strong> {(extra.block_a_extra as Record<string, string>).why_it_matters}</p>
              )}
              {(extra.block_a_extra as Record<string, string>)?.who_has_it && (
                <p><strong>Quien lo tiene:</strong> {(extra.block_a_extra as Record<string, string>).who_has_it}</p>
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
              {(extra.block_b_extra as Record<string, string>)?.differentiator_novelty_grade && (
                <p><strong>Novedad:</strong> {(extra.block_b_extra as Record<string, string>).differentiator_novelty_grade}</p>
              )}
              {(extra.block_b_extra as Record<string, string>)?.trl_evidence && (
                <p><strong>Evidencia TRL:</strong> {(extra.block_b_extra as Record<string, string>).trl_evidence}</p>
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
            <strong>Tecnicos:</strong> {initiative.technical_milestones || "—"}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Economicos:</strong> {initiative.financial_milestones || "—"}
          </p>
          <div className="mt-2">
            <Badge label="Retorno" value={initiative.return_horizon ? `${initiative.return_horizon} meses` : "—"} />
          </div>
        </InfoCard>
      </div>

      {/* Evaluation Results (if exists) */}
      {evaluation && evaluation.results && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-gray-900 pt-4 border-t">
            Resultados del Evaluador
          </h2>

          {/* Derived scores */}
          <div className="grid grid-cols-4 gap-3">
            <ScoreBox
              label="Puntaje Total"
              value={evaluation.results.derived.puntaje_total}
              max={110}
            />
            <ScoreBox
              label="Normalizado"
              value={evaluation.results.derived.puntaje_normalizado}
              max={100}
            />
            <ScoreBox
              label="Novedad"
              value={evaluation.results.derived.novedad}
              max={5}
            />
            <ScoreBox
              label="Incertidumbre"
              value={evaluation.results.derived.indice_incertidumbre}
              max={5}
              precision={1}
            />
          </div>

          {/* Compuertas */}
          <div className="flex gap-3 text-sm">
            <span className="px-3 py-1 rounded bg-gray-100 text-gray-700">
              Sandbox: {evaluation.results.derived.compuerta_sandbox}
            </span>
            <span className="px-3 py-1 rounded bg-gray-100 text-gray-700">
              Innovacion: {evaluation.results.derived.compuerta_innovacion}
            </span>
          </div>

          {/* Dimension scores */}
          <div className="space-y-2">
            {Object.entries(evaluation.results.scores).map(([dim, items]) => (
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
          </div>

          {/* Resumen y recomendacion */}
          <div className="rounded border bg-white p-4 space-y-2">
            <p className="text-sm text-gray-700">
              <strong>Resumen:</strong> {evaluation.results.derived.resumen}
            </p>
            <p className="text-sm text-gray-700">
              <strong>Recomendacion:</strong>{" "}
              {evaluation.results.derived.recomendacion}
            </p>
          </div>

          {/* Veredicto */}
          <div className="rounded border bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">
              Registrar Veredicto del Comite
            </h3>
            {evaluation.veredicto ? (
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">Veredicto actual:</span>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    evaluation.veredicto === "aprobada"
                      ? "bg-green-100 text-green-700"
                      : evaluation.veredicto === "rechazada"
                        ? "bg-red-100 text-red-700"
                        : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {evaluation.veredicto}
                </span>
                {evaluation.reviewed_at && (
                  <span className="text-xs text-gray-400">
                    Validado: {new Date(evaluation.reviewed_at).toLocaleDateString("es-CL")}
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
                  onClick={handleVeredicto}
                  disabled={!veredicto || actionLoading}
                  className="px-3 py-1.5 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading ? "Guardando…" : "Registrar y validar"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Raw DBI text (collapsible) */}
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
