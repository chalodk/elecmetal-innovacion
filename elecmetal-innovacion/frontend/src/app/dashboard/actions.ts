"use server";

import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}

export async function createChatSession(agentType: string = "clara") {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) redirect("/login");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const res = await fetch(`${apiUrl}/api/v1/sessions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ agent_type: agentType, title: agentType === "analista_oportunidad" ? "Analisis de oportunidad" : "Nueva sesion" }),
  });

  if (!res.ok) {
    redirect("/dashboard?error=session_create_failed");
  }

  const data = await res.json();
  redirect(`/dashboard/chat/${data.id}`);
}
