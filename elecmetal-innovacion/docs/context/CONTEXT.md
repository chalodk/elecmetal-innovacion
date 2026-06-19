# Context Module: Plataforma de Innovacion Elecmetal

Modulo de contexto portable para que un agente (humano o IA) continue el desarrollo de la plataforma. Contiene reglas de negocio, modelo de dominio, convenciones de desarrollo y la migracion SQL base.

## Routing Table

| Task | Reference File |
|------|---------------|
| Entender las reglas de negocio | `references/business-rules.md` |
| Entender el modelo de dominio (entidades, relaciones, estados) | `references/domain-model.md` |
| Conocer el stack, convenciones de codigo y estructura del proyecto | `references/development-conventions.md` |
| Ver la migracion SQL base | `references/migration.sql` |
| Implementar un endpoint de la API | `references/development-conventions.md` (API Design) + `references/business-rules.md` |
| Agregar una entidad o modificar el schema | `references/domain-model.md` + `references/development-conventions.md` (Base de Datos) |
| Cambiar la logica de un agente IA | `references/business-rules.md` (Agentes IA) + `references/development-conventions.md` (Agentes IA) |
| Agregar un nuevo rol o permiso | `references/business-rules.md` (Usuarios y Permisos) |
| Entender el ciclo de vida de una iniciativa | `references/domain-model.md` (Maquina de Estados) + `references/business-rules.md` (Flujo de Postulacion) |
| Implementar/entender el parseo del DBI (formato, delimitadores, mapeo a columnas) | `references/dbi-template.md` |
| Configurar el entorno de desarrollo | `references/development-conventions.md` (Setup Inicial) |
| Escribir tests | `references/development-conventions.md` (Testing) |
| Conectar el frontend con Supabase Auth (login, OAuth, callback, middleware) | `references/development-conventions.md` (Autenticacion en el Frontend) |
| Validar el JWT de Supabase en el backend | `references/development-conventions.md` (API Design > Autenticacion) |
| Debuggear loop de login / `__webpack_modules__` | `references/development-conventions.md` (Autenticacion en el Frontend > Lecciones aprendidas) |

## Interaction Modes

### Consultar

El agente lee los archivos de referencia para responder preguntas sobre el proyecto. No modifica nada. Usa la routing table para encontrar el archivo correcto.

Ejemplos:
- "Que hace Clara?" → `references/business-rules.md` (Flujo de Postulacion)
- "Cual es el stack?" → `references/development-conventions.md` (Stack)
- "Como se relacionan sessions e initiatives?" → `references/domain-model.md` (Relaciones)

### Continuar

El agente extiende el proyecto existente: agrega endpoints, modifica el schema, escribe tests. Lee el modulo de contexto, entiende el estado actual del proyecto, y produce codigo que respeta las convenciones establecidas.

Reglas para este modo:
- Seguir las convenciones de codigo en `references/development-conventions.md`
- Respetar las reglas de negocio en `references/business-rules.md`
- Si se modifica el schema, crear una nueva migracion Goose (nunca editar migraciones ya aplicadas)
- Usar los mismos patrones: constraints con nombre explicito, FKs con ON DELETE explicito, COMMENTs en tablas y columnas

### Extender

El agente agrega una capacidad completamente nueva al sistema: un nuevo agente IA, un nuevo tipo de sesion, un nuevo flujo de negocio. Requiere entender el modelo existente y disenar la extension sin romper lo construido.

Reglas para este modo:
- Nuevos agentes conversacionales comparten la estructura `sessions`/`messages` (diferenciados por `agent_type`)
- Nuevos tipos de notificacion se agregan al CHECK de `notification_type`
- Nuevos estados de iniciativa requieren migracion del CHECK constraint
- Las reglas de negocio nuevas deben ser compatibles con las existentes (no contradecirlas)

## Boot Sequence

Orden recomendado para pasar de cero a primer flujo funcional. Cada paso incluye un check minimo verificable.

### Paso 1: Infraestructura

1. Crear proyecto en Supabase (free tier o plan corporativo)
2. Configurar Google OAuth en Supabase Dashboard → `Authentication > Providers` (guia paso a paso en `references/development-conventions.md` > Habilitar Google OAuth en Supabase)
3. Copiar `references/migration.sql` al proyecto y ejecutar con Goose:
   ```bash
   goose -dir migrations postgres "$DATABASE_URL" up
   ```
4. Verificar que las 7 tablas existen, los seeds de `agent_configs` (Clara v5.4, Analista v2, Evaluador v1) estan insertados, y la secuencia `seq_initiative_code` funciona.

**Check**: `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'` devuelve 7 tablas. `SELECT agent_name, version FROM agent_configs WHERE is_active = true` devuelve 3 filas.

### Paso 2: Backend scaffold

1. Crear proyecto FastAPI con estructura segun `references/development-conventions.md` > Estructura del Proyecto
2. Configurar `.env` con `DATABASE_URL` y `SUPABASE_URL` (requeridos). `OPENAI_API_KEY` y `RESEND_API_KEY` se agregan al implementar agentes y notificaciones
3. Implementar pool asyncpg (`core/database.py`) y validacion JWT (`core/security.py`)
4. Health check: `GET /api/v1/health` que verifica conexion a DB

**Check**: `curl http://localhost:8000/api/v1/health` → `{"status": "ok", "database": "connected"}`

### Paso 3: Autenticacion

1. Conectar backend a Supabase Auth: validar que el JWT del header `Authorization: Bearer <token>` es legitimo contra la clave publica de Supabase
2. Endpoint `GET /api/v1/me` que devuelve el perfil del usuario autenticado (lee `profiles` via `auth.users` ID)
3. Verificar que el trigger `handle_new_user()` crea perfiles automaticamente al registrarse

**Check**: Registrarse con Google OAuth. Llamar `GET /api/v1/me` con el token. Recibir `{id, full_name, role: "postulante"}`.

### Paso 4: Frontend scaffold

1. Crear proyecto Next.js 15+ (App Router, codigo en `src/`) con estructura segun `references/development-conventions.md`
2. Configurar `.env.local` con `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` y `NEXT_PUBLIC_API_URL`
3. Configurar los 3 clientes Supabase SSR (`src/lib/supabase/{client,server,middleware}.ts`) — ver `references/development-conventions.md` (Autenticacion en el Frontend)
4. Implementar el flujo de login: pagina publica `login/` (Google OAuth), route handler `auth/callback/route.ts` (intercambio de code) y `middleware.ts` (refresco de sesion + proteccion de rutas, con `/auth/*` y `/login` como publicas)
5. Implementar `dashboard/` protegido: `layout.tsx` (sidebar + `signOut` en `dashboard/actions.ts`) y `page.tsx`
6. Registrar los Redirect URLs en Supabase (`.../auth/callback`, `/login`) para produccion y local (`http://localhost:3000/auth/callback`)

**Check**: Login con Google OAuth → `/auth/callback` intercambia el code → redirect a `/dashboard` → el layout muestra el email del usuario y permite cerrar sesion.

### Paso 5: Chat minimo

1. Scaffold `POST /api/v1/sessions` (crea sesion, `agent_type: 'clara'`, `status: 'active'`)
2. Scaffold `GET /api/v1/sessions` (lista sesiones activas del usuario)
3. Scaffold `POST /api/v1/sessions/{id}/messages` — sin IA aun, responde "Clara no esta disponible. Intentaremos conectarla pronto."
4. Frontend: pagina de chat con area de mensajes + input. Guardar mensajes en DB, mostrar historico al volver a entrar.

**Check**: Crear sesion desde el sidebar. Enviar un mensaje. Recibir respuesta placeholder. Refrescar — los mensajes persisten.

### Paso 6: Integrar Clara

1. En `POST /api/v1/sessions/{id}/messages`:
   - Recuperar todos los mensajes previos de la sesion
   - Cargar prompt y base_knowledge desde `agent_configs WHERE agent_name = 'clara' AND is_active = true`
   - Llamar a OpenAI Chat Completion con `stream: true`
   - Streamear la respuesta al frontend via Server-Sent Events
2. Frontend: leer el stream SSE y renderizar incrementalmente (efecto typewriter)

**Check**: Hablar con Clara. Sigue el prompt v5.4: presenta, pregunta bloque A, avanza paso a paso. La respuesta se streamea en tiempo real.

### Paso 7: DBI — Parseo y persistencia

> **Prerequisito**: aplicar `migrations/002_dbi_v59_alignment.sql`, que alinea `initiatives` con la plantilla v5.9 (TRL/CRL/BRL a entero 1-9, `Tipo` con `mixta`, `return_horizon` en meses, `value_capture` libre, + `dbi_extra JSONB`). Ver `references/dbi-template.md` > Reconciliacion con el esquema actual. Correr: `goose -dir migrations postgres "$DATABASE_URL" up`.

1. Implementar el parser segun `references/dbi-template.md` (contrato de parseo + delimitadores). Anclar con el golden fixture en `backend/tests/fixtures/dbi/`.
2. Cuando Clara indica cierre (el flag definido en el prompt), el backend:
   - Recupera el mensaje que contiene la plantilla DBI (delimitadores predecibles: bordes `═`, cabeceras `A.`–`G.`, lineas de campo `• Label: value`)
   - Parsea encabezado + bloques A-G + pies → estructura normalizada (ver mapeo campo→columna)
   - INSERT en `initiatives` (+ `dbi_extra JSONB` para campos nuevos) con `status = 'persistido'`
   - Autogenera `initiative_code` via `seq_initiative_code` (formato INI-AAAA-NNN)
   - Transiciona sesion a `status = 'completed'`
3. Parseo todo-o-nada: si faltan anclas o un nivel TRL/CRL/BRL es invalido, abortar sin persistir.

**Check**: el parser convierte `example_internal.txt` en `example_internal.expected.json`. Completar una conversacion con Clara genera un registro en `initiatives` con los campos poblados, `initiative_code` generado y `sessions.status = 'completed'`.

### Paso 8: Notificaciones

1. Al persistir iniciativa exitosamente → insertar 2 registros en `notifications` (`receipt_to_applicant` + `notice_to_director`), `status = 'pending'`
2. Job que lee `notifications WHERE status = 'pending'` y dispara envios via Resend/SendGrid
3. Al enviar exitosamente: `status = 'sent'`, `sent_at = now()`
4. Transicionar iniciativa a `status = 'notificado'`

**Check**: Completar postulacion. Dos registros en `notifications`. Si Resend configurado, el postulante recibe email con su initiative_code.

### Paso 9: Evaluacion (directora)

1. Endpoint `PATCH /api/v1/initiatives/{id}/status` → directora mueve iniciativa de `notificado` a `en_evaluacion`
2. Endpoint `POST /api/v1/initiatives/{id}/evaluation` → activa Evaluador, crea registro en `evaluations` con `status = 'in_progress'`
3. Integrar Evaluador (batch: recibe DBI completo, genera columnas 26-38 en JSONB)
4. Al completar: `evaluations.status = 'completed'`, iniciativa → `evaluado`
5. Directora revisa `results` JSONB, puede ajustar, luego `PATCH /api/v1/evaluations/{id}` → iniciativa → `validado`

**Check**: Directora activa evaluacion. Evaluador genera resultados en `evaluations.results`. Directora revisa y valida.

### Paso 10: Panel directora y comité

1. Frontend `(admin)/` protegido: solo rol `directora` o `admin`
2. Vista de iniciativas pendientes de evaluacion
3. Vista de resultados de Evaluador con campos editables
4. Registro de veredicto final (aprobada/rechazada/pendiente) — lo ingresa la directora tras decision del comité

**Check**: Directora ve todas las iniciativas. Activa evaluacion, revisa resultados, registra veredicto.

### Paso 11: Analista de Oportunidad

1. Endpoint `POST /api/v1/sessions` con `agent_type: 'analista_oportunidad'`
2. Misma infraestructura de chat y streaming del Paso 6, pero cargando prompt + skill del Analista v2
3. El Analista recibe 6 campos de entrada (ver `references/business-rules.md` > Analista de Oportunidad) y ejecuta maquina de estados A-L
4. Output: data row + narrativa + slide-ready. Etiquetado DATO/SUPUESTO/DERIVADO.

**Check**: Crear sesion con Analista. Ingresar los 6 campos. Recibir calculo TAM/SAM/SOM. Output etiquetado por tipo de dato.

### Paso 12: Pulido y produccion

1. Implementar paginacion cursor-based en endpoints de listado
2. Agregar filtros y ordenamiento
3. Testing backend (pytest + asyncpg), frontend (Vitest + RTL), migraciones (Up/Down)
4. CI/CD, variables de entorno de produccion, monitoreo

**Check**: Tests pasan. Migraciones Up/Down limpias. Deploy a produccion.

## Project Summary

Plataforma conversacional donde trabajadores de Elecmetal postulan iniciativas de innovacion guiados por Clara (agente IA). La directora de innovacion revisa, evalua y lleva las iniciativas al comité (comite) para decision final.

**Agentes IA**: Clara (postulacion guiada, bloques A-G), Analista de Oportunidad (TAM/SAM/SOM), Evaluador (columnas 26-38).

**Flujo**: Postulante habla con Clara → Clara genera DBI → Sistema parsea 25 campos → Mail a postulante + notificacion a directora → Directora activa Evaluador → comité decide.

**Stack**: Next.js 14+ (frontend), FastAPI (backend), PostgreSQL via Supabase (datos + auth), Goose (migraciones), OpenAI GPT-4o (agentes).
