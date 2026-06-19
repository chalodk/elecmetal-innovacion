"use client";

/**
 * Reusable info card for displaying labeled data in a grid.
 * Used in admin detail pages, dashboard, etc.
 */

interface InfoCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

export default function InfoCard({
  title,
  children,
  className = "",
}: InfoCardProps) {
  return (
    <div className={`rounded border bg-white p-3 ${className}`}>
      <h3 className="text-xs font-semibold uppercase text-gray-400 mb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}
