"use client";

import { createBrowserClient } from "@supabase/ssr";
import { createMockClient, isAuthBypass } from "./mock";

export function createClient() {
  if (isAuthBypass()) return createMockClient();

  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
