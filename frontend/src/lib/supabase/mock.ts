// Usuario y cliente simulados para correr la app sin Supabase (solo dev).
// El bypass se activa cuando NEXT_PUBLIC_AUTH_BYPASS=true o cuando faltan
// las credenciales de Supabase. En produccion siempre debe haber credenciales.

import type { createServerClient } from "@supabase/ssr";

type SupabaseServerClient = ReturnType<typeof createServerClient>;

const MOCK_USER = {
  id: "00000000-0000-0000-0000-000000000000",
  email: "dev@elecmetal.local",
  user_metadata: { full_name: "Usuario Desarrollo" },
};

const MOCK_SESSION = {
  access_token: "dev-bypass-token",
  refresh_token: "dev-bypass-refresh",
  user: MOCK_USER,
};

export function isAuthBypass(): boolean {
  if (process.env.NEXT_PUBLIC_AUTH_BYPASS === "true") return true;
  return (
    !process.env.NEXT_PUBLIC_SUPABASE_URL ||
    !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

// Cliente falso con solo los metodos que usa la app hoy.
export function createMockClient(): SupabaseServerClient {
  return {
    auth: {
      async getUser() {
        return { data: { user: MOCK_USER }, error: null };
      },
      async getSession() {
        return { data: { session: MOCK_SESSION }, error: null };
      },
      async signOut() {
        return { error: null };
      },
    },
  } as unknown as SupabaseServerClient;
}
