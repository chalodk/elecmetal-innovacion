import type { InitiativeStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  InitiativeStatus,
  { label: string; className: string }
> = {
  dbi_generado: {
    label: "DBI Generado",
    className: "bg-gray-100 text-gray-700 border-gray-300",
  },
  persistido: {
    label: "Persistido",
    className: "bg-gray-100 text-gray-700 border-gray-300",
  },
  notificado: {
    label: "Notificado",
    className: "bg-blue-100 text-blue-700 border-blue-300",
  },
  en_evaluacion: {
    label: "En Evaluación",
    className: "bg-orange-100 text-orange-700 border-orange-300",
  },
  evaluado: {
    label: "Evaluado",
    className: "bg-amber-100 text-amber-700 border-amber-300",
  },
  validado: {
    label: "Validado",
    className: "bg-amber-100 text-amber-700 border-amber-300",
  },
  veredicto: {
    label: "Veredicto",
    className: "bg-green-100 text-green-700 border-green-300",
  },
};

interface Props {
  status: InitiativeStatus;
}

export default function InitiativeStatusBadge({ status }: Props) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.dbi_generado;

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
