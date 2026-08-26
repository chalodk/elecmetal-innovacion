import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { signOut } from "./actions";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r border-blue-950 bg-blue-950 p-4 flex flex-col">
        <div className="text-lg font-bold text-white mb-6">
          Elecmetal
        </div>
        <nav className="flex-1 space-y-1">
          <Link
            href="/dashboard"
            className="block rounded px-3 py-2 text-sm text-blue-100 hover:bg-blue-900"
          >
            Inicio
          </Link>
        </nav>
        <div className="border-t border-blue-900 pt-4">
          <p className="text-xs text-blue-200 truncate">{user?.email}</p>
          <form action={signOut}>
            <button className="mt-2 text-xs text-red-400 hover:underline">
              Cerrar sesion
            </button>
          </form>
        </div>
      </aside>
      <main className="flex-1 bg-gray-50 p-8">{children}</main>
    </div>
  );
}
