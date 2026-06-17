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
      <aside className="w-64 border-r bg-white p-4 flex flex-col">
        <div className="text-lg font-bold text-gray-900 mb-6">
          Elecmetal
        </div>
        <nav className="flex-1 space-y-1">
          <Link
            href="/dashboard"
            className="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Inicio
          </Link>
        </nav>
        <div className="border-t pt-4">
          <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          <form action={signOut}>
            <button className="mt-2 text-xs text-red-600 hover:underline">
              Cerrar sesion
            </button>
          </form>
        </div>
      </aside>
      <main className="flex-1 bg-gray-50 p-8">{children}</main>
    </div>
  );
}
