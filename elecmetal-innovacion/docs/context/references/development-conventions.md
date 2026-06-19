# Development Conventions: Plataforma de Innovacion Elecmetal

## Stack

| Componente | Tecnologia | Version |
|------------|-----------|---------|
| Frontend | Next.js | 15.5+ (App Router, `src/`) |
| Backend | FastAPI | 0.110+ |
| Base de datos | PostgreSQL via Supabase | 15+ |
| Autenticacion | Supabase Auth | — |
| Migraciones | Goose | v3+ |
| Agentes IA | OpenAI GPT-4o | — |
| Email | Resend o SendGrid | — |

## Estructura del Proyecto

```
elecmetal-innovacion/
├── frontend/                  # Next.js 15 App Router (codigo en src/)
│   ├── src/
│   │   ├── middleware.ts      # Refresca sesion Supabase + protege rutas
│   │   ├── app/
│   │   │   ├── layout.tsx     # Root layout (fuentes, metadata, <html>)
│   │   │   ├── page.tsx       # "/" → redirect a /dashboard
│   │   │   ├── login/         # Pagina publica de login (Google OAuth)
│   │   │   ├── auth/
│   │   │   │   └── callback/  # Route handler: intercambia code OAuth por sesion
│   │   │   └── dashboard/     # Area autenticada (layout + paginas)
│   │   │       ├── layout.tsx # Sidebar + boton cerrar sesion
│   │   │       ├── page.tsx   # Home del dashboard
│   │   │       └── actions.ts # Server Actions (signOut, etc.)
│   │   └── lib/
│   │       ├── supabase/      # Clientes Supabase SSR (client/server/middleware)
│   │       └── api.ts         # Cliente FastAPI (fetchMe, healthCheck)
│   ├── components/            # (futuro) chat/, initiatives/, ui/
├── backend/                   # FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── agents/    # Endpoints de agentes IA
│   │   │       ├── initiatives/
│   │   │       ├── evaluations/
│   │   │       └── notifications/
│   │   ├── core/
│   │   │   ├── config.py      # Settings desde variables de entorno
│   │   │   ├── security.py    # Validacion JWT Supabase
│   │   │   └── database.py    # Pool de conexiones asyncpg
│   │   ├── models/            # Modelos Pydantic / SQLAlchemy
│   │   ├── services/          # Logica de negocio
│   │   │   ├── clara.py       # Orquestacion de Clara
│   │   │   ├── analista.py    # Orquestacion Analista de Oportunidad
│   │   │   ├── evaluador.py   # Orquestacion Evaluador
│   │   │   ├── dbi_parser.py  # Parseo DBI → 25 campos
│   │   │   └── notifications.py
│   │   ├── workers/           # Procesos de fondo
│   │   │   └── notifications.py  # Worker de envio de emails
│   │   └── agents/            # Definiciones de agentes IA
│   ├── Dockerfile             # Contenedor para Railway
│   ├── railway.toml           # Deploy web service
│   ├── railway.worker.toml    # Deploy worker process
│   └── tests/
├── migrations/                # Archivos Goose .sql
└── skills/                    # Skills de agentes (.skill, .md)
```

## Convenciones de Codigo

### General
- **Lenguaje**: nombres de dominio en espanol, codigo en ingles
- **Formato**: Prettier (frontend), Black (backend)
- **Linting**: ESLint (frontend), Ruff (backend)
- **Tipado**: TypeScript estricto (frontend), type hints + Pydantic (backend)

### Backend (Python/FastAPI)
- **Modelos**: SQLAlchemy 2.0 + asyncpg. No usar ORM para queries complejas — usar `text()` con parametros.
- **Validacion**: Pydantic v2 para request/response schemas
- **Async**: async/await en todos los endpoints que tocan DB o API externa
- **Errores**: formato `{"error": {"code": "INITIATIVE_NOT_FOUND", "message": "...", "details": {}}}`
- **Logging**: structlog con correlation_id por request

### Frontend (Next.js/TypeScript)
- **Ubicacion**: todo el codigo vive en `frontend/src/` (alias `@/` → `src/`). No usar `frontend/app/`.
- **Estado del chat**: `useChat` de Vercel AI SDK o implementacion propia con Server-Sent Events
- **Componentes**: Server Components por defecto, Client Components (`"use client"`) solo cuando se necesita interactividad
- **Estilos**: Tailwind CSS v4 (config en `postcss.config.mjs`, sin `tailwind.config`)
- **Rutas**: App Router con carpetas reales (no route groups): `login/` y `auth/` publicas, `dashboard/` autenticada. La proteccion se hace en `middleware.ts`, no en route groups.
- **Server Actions**: declararlos en archivos dedicados con `"use server"` al inicio del modulo (p.ej. `dashboard/actions.ts`). NO definir Server Actions inline dentro de un Server Component — provoca el error `__webpack_modules__[moduleId] is not a function` en el bundler de Next 15.

### Base de Datos
- **Naming**: tablas en plural snake_case, columnas snake_case, PK `id`, FK `[tabla]_id`
- **Constraints**: siempre con nombre explicito (`pk_`, `fk_`, `uq_`, `ck_`)
- **Migraciones**: Goose. Una migracion por cambio de schema. Nunca editar migraciones ya aplicadas.
- **Queries**: siempre parametrizadas (`$1`, `$2`). Nunca concatenar strings.

## API Design

### RESTful
- Base path: `/api/v1/`
- Recursos en plural: `/api/v1/initiatives`, `/api/v1/sessions`
- Sub-recursos anidados maximo 1 nivel: `/api/v1/sessions/{id}/messages`
- Paginacion: cursor-based con `?cursor=<id>&limit=50`
- Ordenamiento: `?sort=created_at&order=desc`

### Endpoints principales

| Metodo | Path | Descripcion |
|--------|------|-------------|
| POST | `/api/v1/sessions` | Crear sesion con Clara o Analista |
| GET | `/api/v1/sessions/{id}` | Obtener sesion con metadata |
| GET | `/api/v1/sessions/{id}/messages` | Paginar mensajes de sesion |
| POST | `/api/v1/sessions/{id}/messages` | Enviar mensaje (streaming SSE) |
| GET | `/api/v1/initiatives` | Listar iniciativas del usuario |
| GET | `/api/v1/initiatives/{id}` | Obtener iniciativa + DBI completo |
| POST | `/api/v1/initiatives/{id}/evaluation` | Activar evaluacion (solo directora) |
| GET | `/api/v1/evaluations/{id}` | Obtener resultados de evaluacion |
| PATCH | `/api/v1/evaluations/{id}` | Actualizar resultados (solo directora) |

### Autenticacion
- JWT de Supabase en header `Authorization: Bearer <token>`
- Backend valida el JWT via JWKS (ES256) desde `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` (`backend/app/core/security.py`, dependencia `get_current_user`)
- RLS en PostgreSQL como segunda capa (opcional para MVP)

## Autenticacion en el Frontend (Supabase SSR)

El frontend usa `@supabase/ssr` (NO el flujo client-only). La sesion vive en cookies HTTP-only y se comparte entre Server Components, Route Handlers y el middleware. Hay **tres** formas de crear el cliente, segun el contexto de ejecucion:

| Archivo | Helper | Cuando usarlo |
|---------|--------|---------------|
| `src/lib/supabase/client.ts` | `createBrowserClient` | Client Components (`"use client"`), p.ej. el boton de login |
| `src/lib/supabase/server.ts` | `createServerClient` + `cookies()` | Server Components, Route Handlers, Server Actions |
| `src/lib/supabase/middleware.ts` | `createServerClient` sobre `request/response` | Solo dentro de `middleware.ts` |

### Habilitar Google OAuth en Supabase (setup inicial)

Antes de que el flujo de login funcione, el provider de Google debe estar habilitado. Es un proceso de dos lados: Google Cloud Console (genera las credenciales) y Supabase (las consume).

**1. Obtener la URL de callback de Supabase**

En Supabase Dashboard → `Authentication > Providers > Google`. Copiar el "Callback URL (for OAuth)", que tiene la forma:

```
https://<project-ref>.supabase.co/auth/v1/callback
```

> Esta URL es la que Google necesita, NO `http://localhost:3000/auth/callback`. El callback de la app (`/auth/callback`) se registra aparte, en "Redirect URLs" (ver mas abajo).

**2. Crear credenciales en Google Cloud Console** (`console.cloud.google.com`)

1. Crear (o seleccionar) un proyecto.
2. `APIs & Services > OAuth consent screen`: elegir tipo **External**, completar nombre de la app, correo de soporte y dominio. Agregar los scopes basicos (`email`, `profile`, `openid`). Mientras este en modo "Testing", agregar los correos de prueba autorizados.
3. `APIs & Services > Credentials > Create Credentials > OAuth client ID`:
   - Application type: **Web application**.
   - **Authorized JavaScript origins**: el origen de la app (`http://localhost:3000` en local, y el dominio de produccion).
   - **Authorized redirect URIs**: pegar la **Callback URL de Supabase** del paso 1 (`https://<project-ref>.supabase.co/auth/v1/callback`).
4. Guardar y copiar el **Client ID** y el **Client Secret**.

**3. Configurar el provider en Supabase**

1. Supabase Dashboard → `Authentication > Providers > Google` → activar **Enable Sign in with Google**.
2. Pegar **Client ID** y **Client Secret**. Guardar.

**4. Registrar los Redirect URLs de la app**

En `Authentication > URL Configuration` agregar (produccion y local):

- Site URL: el dominio por defecto (p.ej. `http://localhost:3000` en local).
- Redirect URLs: `http://localhost:3000/auth/callback`, `http://localhost:3000/login` y sus equivalentes de produccion (`https://<dominio>/auth/callback`, `/login`).

**Check**: en `/login`, el boton de Google abre el consent screen, se elige una cuenta autorizada y la app redirige a `/dashboard`. Si rebota a `/login?error=auth_callback_error`, revisar que el redirect URI de Google coincida exacto con la callback URL de Supabase, y que el correo este en la lista de testers (si el consent screen esta en modo Testing).

### Flujo de login (Google OAuth)

1. **`/login`** (Client Component): llama `supabase.auth.signInWithOAuth({ provider: "google", options: { redirectTo: \`${origin}/auth/callback\` } })`.
2. Google redirige a **`/auth/callback?code=...`** (Route Handler `route.ts`), que ejecuta `supabase.auth.exchangeCodeForSession(code)` y setea las cookies de sesion.
3. El callback redirige a `/dashboard` (o `?next=`). Si falla, vuelve a `/login?error=auth_callback_error`.
4. **`middleware.ts`** corre en cada request: refresca la sesion y aplica la proteccion de rutas.

### Proteccion de rutas (middleware)

`updateSession` (en `src/lib/supabase/middleware.ts`) define que rutas son publicas:

- Rutas publicas: las que empiezan con `/login` o `/auth`.
- Sin usuario + ruta no publica → redirect a `/login`.
- Con usuario + en `/login` → redirect a `/dashboard`.

> **IMPORTANTE**: `/auth/*` DEBE tratarse como publica. Si el middleware redirige `/auth/callback` a `/login` (porque aun no hay sesion en ese instante), el `code` de OAuth nunca se intercambia y el login entra en loop (la pagina de login se recarga sola).

### Lecciones aprendidas / gotchas

- **Server Actions en archivo aparte**: ver convencion arriba. El `signOut` vive en `dashboard/actions.ts`, no inline en el layout.
- **Limpiar cache tras cambios de directivas**: al mover/agregar `"use client"` / `"use server"`, borrar `.next` (`rm -rf frontend/.next`) y reiniciar `npm run dev` para evitar bundles corruptos.
- **Redirect URLs en Supabase**: en `Authentication > URL Configuration` deben estar registradas tanto produccion (`https://<dominio>/auth/callback`, `/login`) como local (`http://localhost:3000/auth/callback`). El "Site URL" apunta al entorno por defecto.
- **Puerto local**: el frontend corre en `:3000` (backend en `:8000`). Mantener `cors_origins` del backend y los Redirect URLs de Supabase alineados con ese puerto.

## Setup Inicial

```bash
# 1. Clonar repositorio
git clone <repo-url> elecmetal-innovacion
cd elecmetal-innovacion

# 2. Frontend
cd frontend
cp .env.example .env.local
# Editar .env.local con los valores de TU proyecto Supabase:
#   NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY,
#   NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SITE_URL (http://localhost:3000)
npm install
npm run dev

# 3. Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env: DATABASE_URL (requerido), SUPABASE_URL (requerido).
	# OPENAI_API_KEY y RESEND_API_KEY son opcionales al inicio
uvicorn app.main:app --reload

# 4. Migraciones
cd migrations
goose -dir . postgres "$DATABASE_URL" up

# 5. Supabase Auth
# Configurar Google OAuth y Magic Link en Supabase Dashboard
# El trigger handle_new_user() crea profiles automaticamente
```

## Deploy (Railway)

El backend se deploya en Railway con Dockerfile + railway.toml.

- **Root Directory**: `backend/`
- **Config File Path**: `backend/railway.toml`
- **Variables requeridas**: `DATABASE_URL`, `SUPABASE_URL`. `OPENAI_API_KEY` y `RESEND_API_KEY` cuando se implementen agentes y notificaciones.
- **Health check**: Railway usa `GET /api/v1/health` cada 30s.
- **Worker**: servicio separado con `railway.worker.toml`, sin puerto HTTP, ejecuta `python -m app.workers.notifications`.
- **Deploy**: automático desde `main` (GitHub integration).

## Testing

- **Backend**: pytest + asyncpg para tests de integracion contra PostgreSQL real
- **Frontend**: Vitest + React Testing Library para componentes
- **Migraciones**: verificar Up (schema correcto), verificar Down (limpieza total)
- **Agentes IA**: tests con fixtures de conversacion, sin llamadas reales a OpenAI

## Agentes IA

### Configuracion
Los agentes se configuran en `agent_configs` con versionado. El backend carga la version activa al iniciar:
```python
agent = await db.fetchrow(
    "SELECT * FROM agent_configs WHERE agent_name = $1 AND is_active = true",
    "clara"
)
```

### Streaming
Los mensajes del usuario se envian al agente correspondiente via OpenAI API con `stream: true`. La respuesta se streamea al frontend via Server-Sent Events.

### Parseo del DBI
Implementado en `backend/app/services/dbi_parser.py` (`parse_dbi(text) -> dict`). Contrato, delimitadores y mapeo en `docs/context/references/dbi-template.md`. Anclado por el golden fixture (`backend/tests/fixtures/dbi/`) y `tests/test_dbi_parser.py`.

Cuando Clara indica que la conversacion termino (palabra clave o flag en metadata del mensaje), el backend:
1. Recupera todos los mensajes de la sesion
2. Busca el mensaje que contiene la plantilla DBI
3. Llama `parse_dbi()` → estructura normalizada por bloque (parseo todo-o-nada: aborta si faltan anclas o un nivel TRL/CRL/BRL es invalido)
4. Escribe las columnas de `initiatives` + el resto en `dbi_extra JSONB` (ver migr. 002)
5. Transiciona el estado a `persistido`
6. Dispara notificaciones

## Variables de Entorno

```bash
# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
NEXT_PUBLIC_API_URL=http://localhost:8000
# Origen publico de la app: base del redirect OAuth (<SITE_URL>/auth/callback).
# En local debe coincidir con el puerto del dev server (3000).
NEXT_PUBLIC_SITE_URL=http://localhost:3000

# Backend (.env) — requeridos
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
SUPABASE_URL=https://<project-ref>.supabase.co

# Backend (.env) — CORS (incluir el puerto real del frontend)
CORS_ORIGINS=http://localhost:3000

# Backend (.env) — opcionales (agregar al implementar features)
# OPENAI_API_KEY=sk-...
# RESEND_API_KEY=re_...
# SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

> **Puertos en local**: frontend `:3000`, backend `:8000`. `NEXT_PUBLIC_API_URL` debe apuntar al backend y `CORS_ORIGINS` del backend debe incluir el origen del frontend (`http://localhost:3000`), de lo contrario las llamadas `fetch` desde el navegador fallan por CORS.

> **Recursos independientes por dev**: cada desarrollador usa su **propio proyecto Supabase** (BD + provider de Google OAuth propios). Por eso `NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY` (frontend) y `DATABASE_URL`/`SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` (backend) cambian entre devs y nunca se commitean. El Client ID/Secret de Google NO viven en `.env`: se configuran en el dashboard de cada proyecto Supabase (ver "Habilitar Google OAuth en Supabase"). Cada dev debe registrar su propia callback en Google (`{SUPABASE_URL}/auth/v1/callback`) y su `NEXT_PUBLIC_SITE_URL` en los Redirect URLs de Supabase.
