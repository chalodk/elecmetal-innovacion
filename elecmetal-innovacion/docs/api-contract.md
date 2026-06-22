# API Contract v1.0 — Plataforma de Innovación Elecmetal

> **Versión**: 1.0 · **Última actualización**: 2026-06-17
> **Acordado por**: Dev A (backend) · Dev B (frontend)
> **Base**: FastAPI en `:8000` · Consumido por Next.js en `:3000`

---

## 1. Generalidades

### 1.1 Base URL

```
http://localhost:8000/api/v1
```

### 1.2 Autenticación

Toda ruta protegida requiere el header:

```
Authorization: Bearer <supabase-jwt>
```

El backend valida el JWT mediante JWKS (ES256) desde `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`.

Respuesta sin token o con token inválido/expirado:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Token inválido o expirado"
  }
}
```
> **HTTP Status**: `401`

Respuesta con token válido pero sin permisos sobre el recurso (ej: acceder a sesión de otro usuario):

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "No tienes acceso a este recurso"
  }
}
```
> **HTTP Status**: `403`

### 1.3 Formato de error unificado

Toda respuesta de error sigue esta estructura:

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Descripción legible en español",
    "details": {}
  }
}
```

`details` es opcional y contiene información adicional (campo inválido, valor recibido, etc.).

### 1.4 Paginación

Donde aplique, se usa **cursor-based pagination**:

```
GET /api/v1/sessions/{id}/messages?cursor=123&limit=50
```

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `cursor` | integer | — | ID del último elemento de la página anterior |
| `limit` | integer | 50 | Máximo de elementos por página (máx 100) |

Respuesta paginada:

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": 173,
    "has_more": true
  }
}
```

- `next_cursor`: ID del último elemento en esta página. Usar como `?cursor=` para la página siguiente.
- `has_more`: `true` si hay más elementos después de esta página.

### 1.5 Formato de timestamps

Todos los timestamps se devuelven en ISO 8601 con zona horaria:

```
2026-06-17T15:30:00-04:00
```

---

## 2. Health

### `GET /api/v1/health`

**Pública**. No requiere autenticación.

**Response 200**:
```json
{
  "status": "ok",
  "database": "connected"
}
```

Posibles valores de `status`: `"ok"` | `"degraded"`.
Posibles valores de `database`: `"connected"` | `"unreachable"`.

---

## 3. Perfil de usuario

### `GET /api/v1/me`

**Protegida**. Devuelve el perfil del usuario autenticado.

**Response 200**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Camila Gómez",
  "role": "postulante",
  "avatar_url": "https://...",
  "created_at": "2026-06-17T10:00:00-04:00",
  "updated_at": "2026-06-17T10:00:00-04:00"
}
```

**Roles posibles**: `"postulante"` | `"directora"` | `"admin"`

---

## 4. Sesiones

### `POST /api/v1/sessions`

**Protegida**. Crea una nueva sesión de chat con un agente IA.

**Request Body**:
```json
{
  "agent_type": "clara"
}
```

| Campo | Tipo | Requerido | Valores |
|-------|------|-----------|---------|
| `agent_type` | string | Sí | `"clara"` \| `"analista_oportunidad"` |

**Response 201**:
```json
{
  "id": 42,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_type": "clara",
  "status": "active",
  "title": null,
  "started_at": "2026-06-17T15:30:00-04:00",
  "ended_at": null,
  "created_at": "2026-06-17T15:30:00-04:00",
  "updated_at": "2026-06-17T15:30:00-04:00"
}
```

### `GET /api/v1/sessions`

**Protegida**. Lista las sesiones del usuario autenticado.

**Response 200**:
```json
{
  "data": [
    {
      "id": 42,
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "agent_type": "clara",
      "status": "active",
      "title": "Postulación de mejora en molinos...",
      "started_at": "2026-06-17T15:30:00-04:00",
      "ended_at": null,
      "created_at": "2026-06-17T15:30:00-04:00",
      "updated_at": "2026-06-17T15:30:00-04:00"
    }
  ]
}
```

Ordenadas por `created_at` descendente (más recientes primero).
`title` se genera automáticamente con las primeras palabras del primer mensaje del usuario, o es `null` si la sesión no tiene mensajes aún.

### `GET /api/v1/sessions/{id}`

**Protegida**. Obtiene una sesión con su metadata. El usuario solo puede ver sus propias sesiones.

**Response 200**:
```json
{
  "id": 42,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_type": "clara",
  "status": "active",
  "title": "Postulación de mejora en molinos...",
  "started_at": "2026-06-17T15:30:00-04:00",
  "ended_at": null,
  "created_at": "2026-06-17T15:30:00-04:00",
  "updated_at": "2026-06-17T15:30:00-04:00"
}
```

**Response 403** (sesión de otro usuario):
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "No tienes acceso a esta sesión"
  }
}
```

**Response 404**:
```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "La sesión no existe"
  }
}
```

---

## 5. Mensajes

### `GET /api/v1/sessions/{id}/messages`

**Protegida**. Pagina los mensajes de una sesión. El usuario solo puede ver mensajes de sus propias sesiones.

**Query Parameters**:

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `cursor` | integer | — | ID del último mensaje de la página anterior |
| `limit` | integer | 50 | Máximo de mensajes por página (máx 100) |

**Response 200**:
```json
{
  "data": [
    {
      "id": 1001,
      "session_id": 42,
      "role": "user",
      "content": "Quiero postular una mejora para el molino SAG",
      "metadata": null,
      "created_at": "2026-06-17T15:30:05-04:00"
    },
    {
      "id": 1002,
      "session_id": 42,
      "role": "assistant",
      "content": "¡Hola! Soy Clara. Voy a guiarte paso a paso...",
      "metadata": {
        "tokens": 150,
        "block": "A",
        "agent_version": "v5.9"
      },
      "created_at": "2026-06-17T15:30:10-04:00"
    }
  ],
  "pagination": {
    "next_cursor": 1002,
    "has_more": false
  }
}
```

Mensajes ordenados por `created_at` ascendente (los más antiguos primero).

**Roles**: `"user"` | `"assistant"` | `"system"`.

**`metadata`**: objeto opcional con datos del agente (`tokens`, `block`, `agent_version`, etc.).

### `POST /api/v1/sessions/{id}/messages`

**Protegida**. Envía un mensaje del usuario y recibe la respuesta del agente vía **Server-Sent Events (SSE)**.

**Request Body**:
```json
{
  "content": "Quiero postular una mejora para el molino SAG"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `content` | string | Sí | Texto del mensaje del usuario |

**Response**: `Content-Type: text/event-stream`

#### Formato del stream SSE

Cada evento se delimita por `\n\n`. El campo `event` indica el tipo de evento.

##### Evento: `token`

Fragmento incremental de la respuesta del asistente:

```
event: token
data: {"content": "¡Hola"}
```

##### Evento: `done`

El asistente terminó de generar. Incluye el mensaje completo persistido:

```
event: done
data: {"message_id": 1003, "content": "¡Hola! Soy Clara. Voy a guiarte...", "metadata": {"tokens": 150, "block": "A"}}
```

##### Evento: `dbi_ready`

*(Solo para sesiones con Clara)* Se dispara cuando Clara completa el DBI. El frontend debe redirigir a la vista de DBI:

```
event: dbi_ready
data: {"session_id": 42, "message": "He completado el DBI. Puedes revisarlo en tu panel."}
```

##### Evento: `error`

Error en el stream:

```
event: error
data: {"code": "STREAM_ERROR", "message": "Error de conexión con el agente"}
```

##### Evento: `heartbeat`

Cada 15 segundos para mantener la conexión viva:

```
event: heartbeat
data: {}
```

#### Ciclo de vida del stream

```
Cliente                          Servidor
   |                                |
   |-- POST /sessions/42/messages ->|
   |   {"content": "..."}           |
   |                                |-- Persiste mensaje user
   |                                |-- Carga prompt desde agent_configs
   |                                |-- Llama a OpenAI (stream=true)
   |                                |
   |<--- event: token -------------|  (incremental)
   |<--- event: token -------------|
   |<--- event: token -------------|
   |<--- event: done --------------|  (mensaje final persistido)
   |                                |
   |<--- event: dbi_ready ---------|  (solo si Clara terminó el DBI)
   |                                |
   |-- conexión cerrada ------------|
```

#### Manejo de errores del stream

Si el stream se interrumpe (timeout, error de red, error de OpenAI), el servidor envía un evento `error` y cierra la conexión. El frontend debe:

1. Mostrar el error al usuario
2. El mensaje del usuario ya fue persistido (aparece en el historial al refrescar)
3. El mensaje del asistente **no** se persiste si el stream no completó

---

## 6. Iniciativas

### `GET /api/v1/initiatives`

**Protegida**. Lista las iniciativas del usuario autenticado.

**Query Parameters**:

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `status` | string | — | Filtra por estado |
| `cursor` | integer | — | ID del último elemento de la página anterior |
| `limit` | integer | 20 | Máximo por página |

**Response 200**:
```json
{
  "data": [
    {
      "id": 10,
      "initiative_code": "INI-2026-001",
      "title": "Mejora en sistema de molinos SAG",
      "initiative_type": "interna",
      "status": "persistido",
      "area": "Operaciones",
      "applicant_name": "Camila Gómez",
      "postulation_date": "2026-06-17",
      "created_at": "2026-06-17T15:45:00-04:00",
      "updated_at": "2026-06-17T15:45:00-04:00"
    }
  ],
  "pagination": {
    "next_cursor": 10,
    "has_more": false
  }
}
```

Ordenadas por `created_at` descendente.

### `GET /api/v1/initiatives/{id}`

**Protegida**. Obtiene una iniciativa completa con todos los bloques del DBI.

**Response 200**:
```json
{
  "id": 10,
  "session_id": 42,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "initiative_code": "INI-2026-001",
  "status": "persistido",
  "title": "Mejora en sistema de molinos SAG",
  "initiative_type": "interna",
  "postulation_date": "2026-06-17",
  "area": "Operaciones",
  "applicant_name": "Camila Gómez",
  "problem": "El molino SAG presenta desgaste prematuro...",
  "solution": "Recubrimiento con nuevo material compuesto...",
  "economic_impact": "USD 500K/año — Fuente: ahorro en mantenimiento — Beneficiario: Operaciones — Clasificación: OPEX",
  "trl": 5,
  "scalability": "Interna",
  "internal_client": "Superintendencia de Operaciones",
  "external_client": "No aplica",
  "crl": 3,
  "sponsor": "Juan Pérez — Gerente de Operaciones",
  "internal_team": "Ing. Camila Gómez, Ing. Diego Rodríguez",
  "external_team": null,
  "estimated_duration": "8 meses",
  "main_doubt": "Costo del material a escala",
  "key_condition": "Validación en molino piloto",
  "value_capture": "ahorro",
  "brl": 4,
  "technical_milestones": "1. Prueba piloto (mes 1-2), 2. Instalación (mes 3-5), 3. Monitoreo (mes 6-8)",
  "financial_milestones": "Inversión inicial USD 200K, ROI esperado 18 meses",
  "return_horizon": 18,
  "strategic_alignment": null,
  "dbi_raw_text": "═══════════════════════...",
  "dbi_extra": {
    "executive_summary": "Resumen ejecutivo del DBI...",
    "block_a_problem": {
      "problem": "...",
      "why_it_matters": "...",
      "who_has_it": "...",
      "current_solution": "..."
    }
  },
  "created_at": "2026-06-17T15:45:00-04:00",
  "updated_at": "2026-06-17T15:45:00-04:00"
}
```

**Response 403** (iniciativa de otro usuario, excepto si el rol es `directora` o `admin`):
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "No tienes acceso a esta iniciativa"
  }
}
```

**Response 404**:
```json
{
  "error": {
    "code": "INITIATIVE_NOT_FOUND",
    "message": "La iniciativa no existe"
  }
}
```

### `POST /api/v1/initiatives/{id}/evaluation`

**Protegida — solo rol `directora` o `admin`**. Activa al Evaluador para una iniciativa.

**Response 202**:
```json
{
  "evaluation_id": 5,
  "initiative_id": 10,
  "status": "in_progress",
  "message": "Evaluación iniciada. Los resultados estarán disponibles pronto."
}
```

**Response 403** (rol sin permisos):
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Solo la directora puede activar evaluaciones"
  }
}
```

**Response 409** (ya tiene evaluación):
```json
{
  "error": {
    "code": "EVALUATION_EXISTS",
    "message": "Esta iniciativa ya tiene una evaluación en curso o completada"
  }
}
```

---

## 7. Evaluaciones

### `GET /api/v1/evaluations/{id}`

**Protegida — solo rol `directora` o `admin`**. Obtiene los resultados de una evaluación.

**Response 200**:
```json
{
  "id": 5,
  "initiative_id": 10,
  "activated_by": "660e8400-e29b-41d4-a716-446655440001",
  "status": "completed",
  "results": {
    "columns": {}
  },
  "reviewed_by": null,
  "reviewed_at": null,
  "veredicto": null,
  "created_at": "2026-06-17T16:00:00-04:00",
  "updated_at": "2026-06-17T16:05:00-04:00"
}
```

**Response 403** (rol sin permisos):
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Solo la directora puede ver evaluaciones"
  }
}
```

### `PATCH /api/v1/evaluations/{id}`

**Protegida — solo rol `directora` o `admin`**. Revisa los resultados y emite un veredicto.

**Request Body**:
```json
{
  "veredicto": "aprobada"
}
```

| Campo | Tipo | Requerido | Valores |
|-------|------|-----------|---------|
| `veredicto` | string | Sí | `"aprobada"` \| `"rechazada"` \| `"pendiente"` |

**Response 200**:
```json
{
  "id": 5,
  "initiative_id": 10,
  "veredicto": "aprobada",
  "reviewed_by": "660e8400-e29b-41d4-a716-446655440001",
  "reviewed_at": "2026-06-17T17:00:00-04:00",
  "updated_at": "2026-06-17T17:00:00-04:00"
}
```

---

## 8. Resumen de códigos de error

| HTTP | code | Significado |
|------|------|-------------|
| 400 | `VALIDATION_ERROR` | Body inválido o campo faltante |
| 401 | `UNAUTHORIZED` | Token faltante, inválido o expirado |
| 403 | `FORBIDDEN` | Token válido pero sin permisos sobre el recurso |
| 404 | `SESSION_NOT_FOUND` | La sesión no existe |
| 404 | `INITIATIVE_NOT_FOUND` | La iniciativa no existe |
| 404 | `EVALUATION_NOT_FOUND` | La evaluación no existe |
| 409 | `EVALUATION_EXISTS` | La iniciativa ya tiene evaluación |
| 500 | `INTERNAL_ERROR` | Error inesperado del servidor |

---

## 9. Estados de iniciativa

```
dbi_generado → persistido → notificado → en_evaluacion → evaluado → validado → veredicto
```

| Estado | Significado | Quién lo dispara |
|--------|-------------|------------------|
| `dbi_generado` | Clara generó el DBI | Clara (IA) |
| `persistido` | DBI parseado y guardado en BD | Sistema |
| `notificado` | Emails enviados al postulante y directora | Sistema |
| `en_evaluacion` | Directora activó al Evaluador | Directora |
| `evaluado` | Evaluador generó resultados | Evaluador (IA) |
| `validado` | Directora revisó resultados | Directora |
| `veredicto` | Decisión final emitida | Directora |

---

## 10. Notas para el frontend (Dev B)

### Durante el Día 0

Mientras el backend no tenga los endpoints listos, el frontend puede trabajar con **mocks** que respeten este contrato. Ejemplo con un helper:

```typescript
// frontend/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchMe(): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/api/v1/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.json();
    throw new ApiError(res.status, body.error);
  }
  return res.json();
}
```

Hasta que el backend esté listo, se puede usar un mock:

```typescript
const MOCK_ME: UserProfile = {
  id: "mock-user-id",
  full_name: "Camila (mock)",
  role: "postulante",
  avatar_url: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};
```

### SSE en el frontend

Para consumir el stream en B2, usar `EventSource` o `fetch` con `ReadableStream`:

```typescript
const response = await fetch(`${API_BASE}/api/v1/sessions/${id}/messages`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({ content: message }),
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  // Parsear eventos SSE del chunk...
}
```

### React Query (B1)

Para el dashboard y la lista de sesiones, usar React Query:

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ["sessions"],
  queryFn: () => fetchSessions(),
});
```

---

## 11. Changelog

| Fecha | Versión | Cambios |
|-------|---------|---------|
| 2026-06-17 | 1.0 | Contrato inicial. Endpoints de health, me, sessions, messages (SSE), initiatives, evaluations. |
