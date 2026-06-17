import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { fetchMe } from "@/lib/api";
import { cookies } from "next/headers";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) redirect("/login");

  let profile: { full_name?: string; role?: string } = {};
  try {
    profile = await fetchMe(session.access_token);
  } catch {
    // Backend no disponible — mostrar datos basicos de Supabase
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <p className="text-sm text-gray-600">
          Bienvenido,{" "}
          <span className="font-medium text-gray-900">
            {profile.full_name || session.user.email}
          </span>
        </p>
        <p className="mt-1 text-xs text-gray-400">
          Rol: {profile.role || "postulante"}
        </p>
      </div>
    </div>
  );
}
