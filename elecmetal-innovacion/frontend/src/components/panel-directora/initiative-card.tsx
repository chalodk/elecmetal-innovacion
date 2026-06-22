import type { Initiative } from "@/lib/types";
import InitiativeStatusBadge from "./initiative-status-badge";

interface Props {
  initiative: Initiative;
  onClick: (id: number) => void;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  return date.toLocaleDateString("es-CL", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const TYPE_LABELS: Record<string, string> = {
  interna: "Interna",
  externa: "Externa",
  mixta: "Mixta",
};

export default function InitiativeCard({ initiative, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={() => onClick(initiative.id)}
      className="w-full rounded-lg border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-gray-400">
              {initiative.initiative_code}
            </span>
            <span className="text-xs text-gray-300">·</span>
            <span className="text-xs text-gray-500">
              {TYPE_LABELS[initiative.initiative_type] ?? initiative.initiative_type}
            </span>
          </div>
          <h3 className="mt-1 truncate text-sm font-semibold text-gray-900">
            {initiative.title}
          </h3>
          <p className="mt-1 text-xs text-gray-500">
            {initiative.applicant_name} · {initiative.area} ·{" "}
            {formatDate(initiative.postulation_date)}
          </p>
        </div>
        <InitiativeStatusBadge status={initiative.status} />
      </div>
    </button>
  );
}
