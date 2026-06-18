import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { signOut, createChatSession } from "./actions";

async function fetchSessions(token: string) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/api/v1/sessions`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return [];
    const body = await res.json();
    // Handle paginated envelope vs raw array (backward compat)
    return Array.isArray(body) ? body : (body.data || []);
  } catch {
    return [];
  }
}

const createClaraSession = createChatSession.bind(null, "clara");
const createAnalistaSession = createChatSession.bind(null, "analista_oportunidad");

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const { data: { session } } = await supabase.auth.getSession();

  const sessions = session?.access_token
    ? await fetchSessions(session.access_token)
    : [];

  const claraSessions = sessions.filter(
    (s: { agent_type: string }) => s.agent_type === "clara",
  );
  const analistaSessions = sessions.filter(
    (s: { agent_type: string }) => s.agent_type === "analista_oportunidad",
  );

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r bg-white p-4 flex flex-col">
        <div className="text-lg font-bold text-gray-900 mb-6">
          Elecmetal
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto">
          <Link
            href="/dashboard"
            className="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Inicio
          </Link>

          {/* Clara sessions */}
          <div className="pt-4">
            <div className="flex items-center justify-between px-3 pb-1">
              <span className="text-xs font-semibold uppercase text-gray-400">
                Clara
              </span>
              <form action={createClaraSession}>
                <button className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                  + Nueva
                </button>
              </form>
            </div>

            {claraSessions.length === 0 ? (
              <p className="px-3 py-2 text-xs text-gray-400 italic">
                Sin sesiones
              </p>
            ) : (
              <div className="space-y-0.5">
                {claraSessions.map((s: { id: string; title: string }) => (
                  <Link
                    key={s.id}
                    href={`/dashboard/chat/${s.id}`}
                    className="block rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 truncate"
                  >
                    {s.title || `Sesion ${s.id}`}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Analista sessions */}
          <div className="pt-4">
            <div className="flex items-center justify-between px-3 pb-1">
              <span className="text-xs font-semibold uppercase text-gray-400">
                Analista
              </span>
              <form action={createAnalistaSession}>
                <button className="text-xs text-purple-600 hover:text-purple-800 font-medium">
                  + Nueva
                </button>
              </form>
            </div>

            {analistaSessions.length === 0 ? (
              <p className="px-3 py-2 text-xs text-gray-400 italic">
                Sin analisis
              </p>
            ) : (
              <div className="space-y-0.5">
                {analistaSessions.map((s: { id: string; title: string }) => (
                  <Link
                    key={s.id}
                    href={`/dashboard/chat/${s.id}`}
                    className="block rounded px-3 py-1.5 text-sm text-purple-600 hover:bg-purple-50 truncate"
                  >
                    {s.title || `Analisis ${s.id}`}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </nav>

        {/* Admin link for directora */}
        <div className="pt-3 border-t">
          <Link
            href="/dashboard/admin"
            className="block rounded px-3 py-2 text-xs text-gray-500 hover:bg-gray-100"
          >
            Panel Directora
          </Link>
        </div>

        <div className="pt-3 border-t">
          <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          <form action={signOut}>
            <button className="mt-2 text-xs text-red-600 hover:underline">
              Cerrar sesion
            </button>
          </form>
        </div>
      </aside>
      <main className="flex-1 bg-gray-50 flex flex-col">{children}</main>
    </div>
  );
}
