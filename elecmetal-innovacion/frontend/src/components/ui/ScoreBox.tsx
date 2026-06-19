"use client";

/**
 * Score display box with progress bar.
 * Used in evaluation detail views.
 */

interface ScoreBoxProps {
  label: string;
  value: number;
  max: number;
  precision?: number;
  className?: string;
}

export default function ScoreBox({
  label,
  value,
  max,
  precision = 0,
  className = "",
}: ScoreBoxProps) {
  const pct = Math.min(100, Math.round((value / max) * 100));

  return (
    <div
      className={`rounded border bg-white p-3 text-center ${className}`}
    >
      <p className="text-2xl font-bold text-gray-900">
        {value.toFixed(precision)}
        <span className="text-sm text-gray-400 font-normal">
          /{max}
        </span>
      </p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
      <div className="mt-1 h-1 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${
            pct >= 70
              ? "bg-green-500"
              : pct >= 40
                ? "bg-yellow-500"
                : "bg-red-500"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
