import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { redirect } from "next/navigation";
import { fetchMe } from "@/lib/api";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) redirect("/login");

  // Verify role — only directora/admin can access
  let role = "";
  try {
    const profile = await fetchMe(session.access_token);
    role = profile.role || "";
  } catch {
    // fallback: allow access, backend will enforce
  }

  if (role && role !== "directora" && role !== "admin") {
    redirect("/dashboard");
  }

  return (
    <div className="flex min-h-0 flex-1">
      {/* Admin sidebar */}
      <aside className="w-56 border-r bg-white p-4 flex flex-col flex-shrink-0">
        <div className="text-sm font-bold text-gray-900 mb-1">Panel Directora</div>
        <p className="text-xs text-gray-400 mb-4">Gestion de innovacion</p>
        <nav className="flex-1 space-y-0.5 overflow-y-auto">
          <Link
            href="/dashboard/admin"
            className="block rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            Iniciativas
          </Link>
          <Link
            href="/dashboard"
            className="block rounded px-3 py-1.5 text-xs text-gray-400 hover:bg-gray-100 mt-4"
          >
            ← Volver al menu
          </Link>
        </nav>
        <div className="border-t pt-3 mt-3">
          <p className="text-xs text-gray-500 truncate">
            {session.user.email}
          </p>
          <p className="text-xs text-blue-600 font-medium">{role || "admin"}</p>
        </div>
      </aside>
      <main className="flex-1 bg-gray-50 flex flex-col min-h-0 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
