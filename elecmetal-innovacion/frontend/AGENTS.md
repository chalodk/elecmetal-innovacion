<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Convenciones del frontend (Elecmetal Innovacion)

Next.js 15.5 (App Router). Todo el codigo vive en `src/` (alias `@/` → `src/`). El dev server corre en el puerto **3000** (backend FastAPI en `:8000`).

## Estructura

- `src/middleware.ts` — refresca la sesion de Supabase y protege rutas.
- `src/app/login/` — pagina publica de login (Google OAuth, Client Component).
- `src/app/auth/callback/route.ts` — intercambia el `code` de OAuth por sesion.
- `src/app/dashboard/` — area autenticada (`layout.tsx`, `page.tsx`, `actions.ts`).
- `src/lib/supabase/{client,server,middleware}.ts` — clientes Supabase SSR.
- `src/lib/api.ts` — cliente del backend FastAPI.

## Autenticacion (Supabase SSR)

Usar `@supabase/ssr`, nunca el flujo client-only. Elegir el cliente segun contexto:
- Client Component → `createClient` de `@/lib/supabase/client`.
- Server Component / Route Handler / Server Action → `createClient` de `@/lib/supabase/server`.
- Dentro de `middleware.ts` → helper de `@/lib/supabase/middleware`.

En el middleware, `/login` y `/auth/*` SON publicas. Si `/auth/callback` no es publica, el login entra en loop (no alcanza a intercambiar el code OAuth).

## Reglas que evitan bugs ya vividos

- **Server Actions van en archivos con `"use server"` al inicio del modulo** (p.ej. `dashboard/actions.ts`). Nunca definir un Server Action inline dentro de un Server Component → provoca `__webpack_modules__[moduleId] is not a function`.
- Tras mover/agregar directivas `"use client"`/`"use server"`, borrar `.next` y reiniciar el dev server.
- Mantener alineados el puerto 3000, los Redirect URLs de Supabase (`http://localhost:3000/auth/callback`) y `CORS_ORIGINS` del backend.

Referencia completa: `../docs/context/references/development-conventions.md` (seccion "Autenticacion en el Frontend").
