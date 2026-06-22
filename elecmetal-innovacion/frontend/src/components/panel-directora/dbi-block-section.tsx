"use client";

import { useState } from "react";

interface Field {
  label: string;
  value: string | number | null | undefined;
}

interface Props {
  title: string;
  letter: string;
  fields: Field[];
  defaultOpen?: boolean;
}

function formatValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return String(value);
  const trimmed = value.trim();
  if (!trimmed) return "—";
  const lower = trimmed.toLowerCase();
  if (["no especificado", "no aplica", "no definido", "ninguno", "ninguna"].includes(lower)) {
    return "—";
  }
  return trimmed;
}

export default function DbiBlockSection({
  title,
  letter,
  fields,
  defaultOpen = false,
}: Props) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
      >
        <span className="text-sm font-semibold text-gray-900">
          <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded bg-blue-100 text-xs font-bold text-blue-700">
            {letter}
          </span>
          {title}
        </span>
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="border-t border-gray-100 px-4 py-3">
          <dl className="space-y-2">
            {fields.map((field) => (
              <div key={field.label}>
                <dt className="text-xs font-medium text-gray-500">{field.label}</dt>
                <dd className="mt-0.5 text-sm text-gray-900 whitespace-pre-wrap">
                  {formatValue(field.value)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}
