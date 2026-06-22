import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { fetchMe } from "@/lib/api";
import Link from "next/link";

export default async function PanelDirectoraLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/login");
  }

  let role = "postulante";

  try {
    const profile = await fetchMe(session.access_token);
    role = profile.role;
  } catch {
    // Backend no disponible — redirigir a dashboard
    redirect("/dashboard");
  }

  if (role !== "directora" && role !== "admin") {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              ← Dashboard
            </Link>
            <span className="text-gray-300">|</span>
            <h1 className="text-lg font-semibold text-gray-900">
              Panel Directora
            </h1>
          </div>
          <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-700">
            {role === "admin" ? "Admin" : "Directora"}
          </span>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-6xl px-6 py-6">{children}</main>
    </div>
  );
}
