"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  listInitiatives,
  updateInitiativeStatus,
  triggerEvaluation,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui";

interface Initiative {
  id: number;
  initiative_code: string;
  title: string;
  initiative_type: string;
  status: string;
  applicant_name: string;
  area: string;
  postulation_date: string;
  created_at: string;
}

const STATUS_LABELS: Record<string, string> = {
  persistido: "Persistido",
  notificado: "Notificado",
  en_evaluacion: "En evaluacion",
  evaluado: "Evaluado",
  validado: "Validado",
  veredicto: "Veredicto",
};

const TABS = [
  { key: "all", label: "Todas" },
  { key: "notificado", label: "Pendientes" },
  { key: "en_evaluacion", label: "En evaluacion" },
  { key: "evaluado", label: "Evaluadas" },
  { key: "validado", label: "Validadas" },
];

export default function AdminPage() {
  const router = useRouter();
  const [initiatives, setInitiatives] = useState<Initiative[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("notificado");
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push("/login"); return; }
      const data = await listInitiatives(session.access_token);
      // Handle paginated envelope vs raw array
      setInitiatives(Array.isArray(data) ? data : (data.data || []));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => { load(); }, [load]);

  const filtered = activeTab === "all"
    ? initiatives
    : initiatives.filter((i) => i.status === activeTab);

  // ── Actions ───────────────────────────────────────────────────────────

  const handleMoveToEvaluation = async (initiativeId: number) => {
    setActionLoading(initiativeId);
    setError(null);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      await updateInitiativeStatus(
        session.access_token, String(initiativeId), "en_evaluacion",
      );
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleTriggerEvaluator = async (initiativeId: number) => {
    setActionLoading(initiativeId);
    setError(null);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      await triggerEvaluation(session.access_token, String(initiativeId));
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionLoading(null);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center flex-1">
        <p className="text-sm text-gray-400">Cargando iniciativas…</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">
          Panel de Directora
        </h1>
        <button
          onClick={load}
          className="text-xs text-blue-600 hover:underline"
        >
          Refrescar
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b pb-0">
        {TABS.map((tab) => {
          const count = tab.key === "all"
            ? initiatives.length
            : initiatives.filter((i) => i.status === tab.key).length;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
                activeTab === tab.key
                  ? "bg-white border border-b-white -mb-px text-gray-900"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
              {count > 0 && (
                <span className="ml-1.5 bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5 text-xs">
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Initiative list */}
      {filtered.length === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center">
          <p className="text-sm text-gray-400">
            No hay iniciativas en &quot;{STATUS_LABELS[activeTab] || activeTab}&quot;
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((init) => (
            <div
              key={init.id}
              className="rounded-lg border bg-white p-4 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs text-gray-400">
                      {init.initiative_code}
                    </span>
                    <StatusBadge status={init.status} />
                    <span className="text-xs text-gray-400 capitalize">
                      {init.initiative_type}
                    </span>
                  </div>
                  <h3
                    className="text-sm font-medium text-gray-900 cursor-pointer hover:text-blue-600"
                    onClick={() =>
                      router.push(
                        `/dashboard/admin/initiatives/${init.id}`,
                      )
                    }
                  >
                    {init.title}
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {init.applicant_name} · {init.area}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {init.status === "notificado" && (
                    <button
                      onClick={() => handleMoveToEvaluation(init.id)}
                      disabled={actionLoading === init.id}
                      className="px-2.5 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200 disabled:opacity-50 transition-colors"
                    >
                      {actionLoading === init.id
                        ? "…"
                        : "Enviar a evaluacion"}
                    </button>
                  )}

                  {init.status === "en_evaluacion" && (
                    <button
                      onClick={() => handleTriggerEvaluator(init.id)}
                      disabled={actionLoading === init.id}
                      className="px-2.5 py-1 text-xs font-medium rounded bg-purple-100 text-purple-700 hover:bg-purple-200 disabled:opacity-50 transition-colors"
                    >
                      {actionLoading === init.id
                        ? "Evaluando…"
                        : "Activar Evaluador"}
                    </button>
                  )}

                  {(init.status === "evaluado" ||
                    init.status === "validado") && (
                    <button
                      onClick={() =>
                        router.push(
                          `/dashboard/admin/initiatives/${init.id}`,
                        )
                      }
                      className="px-2.5 py-1 text-xs font-medium rounded bg-white border text-gray-600 hover:bg-gray-50 transition-colors"
                    >
                      Ver evaluacion
                    </button>
                  )}

                  <button
                    onClick={() =>
                      router.push(
                        `/dashboard/admin/initiatives/${init.id}`,
                      )
                    }
                    className="text-xs text-gray-400 hover:text-gray-600"
                  >
                    Detalle →
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
