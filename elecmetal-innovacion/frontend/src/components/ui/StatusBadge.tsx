"use client";

/**
 * Reusable status badge component.
 * Maps status strings to consistent color-coded badges.
 */

const STATUS_COLORS: Record<string, string> = {
  // Initiatives (colores mergeados Jorge + Diego)
  dbi_generado: "bg-gray-100 text-gray-700",
  persistido: "bg-gray-100 text-gray-700",
  notificado: "bg-blue-100 text-blue-700",
  en_evaluacion: "bg-orange-100 text-orange-700",
  evaluado: "bg-amber-100 text-amber-700",
  validado: "bg-amber-100 text-amber-700",
  veredicto: "bg-green-100 text-green-700",
  // Sessions
  active: "bg-green-100 text-green-700",
  completed: "bg-gray-100 text-gray-600",
  abandoned: "bg-red-100 text-red-600",
  // Evaluations
  pending: "bg-gray-100 text-gray-600",
  in_progress: "bg-yellow-100 text-yellow-700",
  // Notifications
  sent: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  // Veredicto
  aprobada: "bg-green-100 text-green-700",
  rechazada: "bg-red-100 text-red-700",
  pendiente: "bg-yellow-100 text-yellow-700",
};

const STATUS_LABELS: Record<string, string> = {
  dbi_generado: "DBI Generado",
  persistido: "Persistido",
  notificado: "Notificado",
  en_evaluacion: "En Evaluación",
  evaluado: "Evaluado",
  validado: "Validado",
  veredicto: "Veredicto",
  active: "Activo",
  completed: "Completado",
  abandoned: "Abandonado",
  pending: "Pendiente",
  in_progress: "En progreso",
  sent: "Enviado",
  failed: "Fallido",
  aprobada: "Aprobada",
  rechazada: "Rechazada",
};

interface StatusBadgeProps {
  status: string;
  label?: string;
  className?: string;
}

export default function StatusBadge({
  status,
  label,
  className = "",
}: StatusBadgeProps) {
  const colorClass =
    STATUS_COLORS[status] || "bg-gray-100 text-gray-600";
  const displayLabel = label || STATUS_LABELS[status] || status;

  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${colorClass} ${className}`}
    >
      {displayLabel}
    </span>
  );
}
