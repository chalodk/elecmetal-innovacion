"use client";

import { createClient } from "@/lib/supabase/client";

/**
 * Obtiene el access_token de la sesión actual de Supabase.
 * Solo funciona en Client Components.
 */
export async function getAccessToken(): Promise<string> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  if (!data.session?.access_token) {
    throw new Error("No hay sesión activa");
  }
  return data.session.access_token;
}
