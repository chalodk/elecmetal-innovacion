import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { fetchMe } from "@/lib/api";
import ProfileCard from "@/components/dashboard/profile-card";
import WelcomeState from "@/components/dashboard/welcome-state";
import ChatView from "@/components/chat/chat-view";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ session_id?: string }>;
}) {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  const { data: { user } } = await supabase.auth.getUser();

  if (!session) redirect("/login");

  let fullName = user?.email ?? "Usuario";
  let role = "postulante";

  try {
    const profile = await fetchMe(session.access_token);
    fullName = profile.full_name;
    role = profile.role;
  } catch {
    // Backend no disponible — mostrar datos básicos de Supabase
  }

  // Leer session_id de la URL para mostrar el chat
  const params = searchParams ? await searchParams : {};
  const sessionId = params.session_id ? Number(params.session_id) : null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      <ProfileCard fullName={fullName} role={role} />

      {sessionId ? (
        <ChatView sessionId={sessionId} />
      ) : (
        <>
          <WelcomeState hasSessions={false} />
          <div className="rounded-lg border bg-white p-8 text-center">
            <p className="text-sm text-gray-400">
              Selecciona una sesión en el panel izquierdo para comenzar a chatear.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
