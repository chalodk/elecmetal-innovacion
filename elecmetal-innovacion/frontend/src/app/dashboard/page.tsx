import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { fetchMe, listInitiatives } from "@/lib/api";
import Link from "next/link";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) redirect("/login");

  let profile: { full_name?: string; role?: string } = {};
  let initiatives: Array<{
    id: number;
    initiative_code: string;
    title: string;
    status: string;
    initiative_type: string;
    created_at: string;
  }> = [];

  try {
    profile = await fetchMe(session.access_token);
    const result = await listInitiatives(session.access_token);
    // Handle paginated envelope: {data: [...], pagination: {...}}
    initiatives = Array.isArray(result) ? result : (result.data || []);
  } catch {
    // Backend no disponible — mostrar datos basicos
  }

  return (
    <div className="space-y-6 p-8">
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

      {/* Initiatives section */}
      {initiatives.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-800">
            Mis Iniciativas
          </h2>
          <div className="space-y-2">
            {initiatives.map((init) => (
              <Link
                key={init.id}
                href={`/dashboard/initiatives/${init.id}`}
                className="block rounded-lg border bg-white p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-gray-400">
                        {init.initiative_code}
                      </span>
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                        {init.status}
                      </span>
                      <span className="text-xs text-gray-400 capitalize">
                        {init.initiative_type}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {init.title}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400 flex-shrink-0 ml-4">
                    {new Date(init.created_at).toLocaleDateString("es-CL")}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border bg-white p-8 text-center">
          <p className="text-sm text-gray-500">
            No tienes iniciativas todavia.
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Inicia una conversacion con Clara desde el sidebar para postular
            tu primera iniciativa.
          </p>
        </div>
      )}
    </div>
  );
}
