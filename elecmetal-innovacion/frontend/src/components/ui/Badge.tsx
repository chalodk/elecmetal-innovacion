"use client";

/**
 * Reusable badge for displaying label: value pairs.
 */

interface BadgeProps {
  label: string;
  value: unknown;
  className?: string;
}

export default function Badge({ label, value, className = "" }: BadgeProps) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded bg-gray-100 text-gray-600 font-medium text-xs ${className}`}
    >
      {label}: {String(value)}
    </span>
  );
}
