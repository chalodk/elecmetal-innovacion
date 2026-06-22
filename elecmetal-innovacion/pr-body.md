## ⚠️ Leer antes de mergear — solapamiento con PRs de Jorge (#10, #11, #12)

@chalodk Este PR contiene el trabajo de **dev-b** (Diego): B1, B2, B3 + Step 6 (OpenAI). 
Anoche Jorge (dev-a) subió los PRs #10, #11, #12 con A1, A2, A3. Hay **solapamiento en backend**. 
Ambos construimos `sessions.py`, `initiatives.py`, `security.py`, `main.py` — por separado.

---

### Estrategia de merge recomendada

**1. Mergear PRs de Jorge primero** en este orden: [#10](https://github.com/chalodk/elecmetal-innovacion/pull/10) → [#11](https://github.com/chalodk/elecmetal-innovacion/pull/11) → [#12](https://github.com/chalodk/elecmetal-innovacion/pull/12)
- Son el backend canónico con 99 tests
- Tienen infraestructura que nosotros no: `errors.py`, `pagination.py`, `models/domain.py`, migración 003, worker de notificaciones

**2. Rebasear este PR sobre main** (después del merge de Jorge). Archivos con conflicto:
| Archivo | Estrategia |
|---------|-----------|
| `sessions.py` | Base de Jorge + wire de nuestro `agent_runner.py` |
| `initiatives.py` | El de Jorge (tiene GET+POST+DBI persist) |
| `security.py` | Validators de Jorge + nuestro `require_role()` |
| `main.py` | Routers de Jorge + nuestro initiatives_router |
| `agent_runner.py` | Evaluar fusionarlo con `ClaraService` de Jorge |

**3. Nuestro frontend NO tiene conflicto** — no toca nada de Jorge.

---

### Qué trae este PR (dev-b)

**6 commits en `feature/b1-dashboard-sidebar-sesiones`:**

| Commit | Issue | Qué |
|--------|-------|-----|
| `db6b7a2` | #5 B1 | Dashboard real + sidebar de sesiones |
| `372201f` | #6 B2 | UI de chat con SSE streaming + typewriter + tests |
| `31f57b9` | B2+B3 | API de mensajes + SSE endpoint + integración ChatView |
| `c8c38ed` | Step 6 | Integrar Clara (OpenAI) — `agent_runner.py`, streaming real GPT-4o |
| `356ef86` | #7 B3 | Panel directora: lista + detalle DBI con bloques A-G |
| `2c7948f` | fix | Tests: 65/65 pasando |

### Backend (archivos con posible conflicto)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/me` | GET | Perfil del usuario autenticado |
| `/api/v1/sessions` | GET/POST | Listar y crear sesiones |
| `/api/v1/sessions/{id}` | GET | Detalle de sesión |
| `/api/v1/sessions/{id}/messages` | GET/POST | Paginar mensajes, enviar mensaje |
| `/api/v1/sessions/{id}/stream` | GET | SSE streaming con OpenAI GPT-4o (con fallback si no hay API key) |
| `/api/v1/initiatives` | GET | Listado con filtro por status, paginación cursor-based |
| `/api/v1/initiatives/{id}` | GET | Detalle completo con evaluación (LEFT JOIN) |

**Servicios nuevos:**
- `app/services/agent_runner.py` — `stream_agent_response()`, `persist_assistant_message()`
- `app/core/security.py` — agregado `require_role("directora", "admin")`

### Frontend (sin conflicto, todo nuevo)

**Rutas:**
- `/dashboard` — Dashboard postulante con sidebar + chat + SSE typewriter
- `/panel-directora` — Layout protegido por rol directora/admin
- `/panel-directora/[id]` — Detalle DBI con bloques colapsables A-G + evaluación

**Componentes nuevos (20 archivos):**
- Chat: `ChatView`, `ChatInput`, `MessageBubble`, `MessageList`
- Panel: `InitiativeCard`, `InitiativeStatusBadge`, `DbiBlockSection`
- Layout: `Sidebar` (actualizado), `ProfileCard`, `WelcomeState`, `NewSessionModal`
- Hooks: `useChatStream`, `useInitiatives`, `useInitiative`, `useMessages`, `useSessions`
- SSE: `sse-client.ts` con reconexión exponential backoff

### Tests

```
✓ 65/65 tests pasando (10 test files)
  6 componentes + 2 hooks + 2 integración
```

### Cómo probar

**Con OpenAI** (configurar `OPENAI_API_KEY=sk-...` en `backend/.env`):
1. Login → Dashboard → "+ Nueva sesión" → seleccionar Clara
2. Enviar mensaje → respuesta streaming real de GPT-4o (typewriter)
3. Sidebar muestra link "Panel Directora" si el usuario es directora/admin
4. `/panel-directora` → lista de iniciativas mock (3 con distintos estados)
5. Click en iniciativa → detalle DBI completo con bloques A-G colapsables

**Sin OpenAI** (sin configurar key): mismo flujo, response placeholder.

---

### Resumen de issues

| Issue | Estado |
|-------|--------|
| #5 B1 — Dashboard + sidebar | ✅ |
| #6 B2 — UI chat SSE streaming | ✅ |
| #7 B3 — Panel directora mínimo | ✅ |
| #2 A1 — API sesiones/mensajes | ⚠️ Cubierto pero duplicado con PR #10 |
| #3 A2 — Chat Clara (SSE + OpenAI) | ⚠️ Cubierto pero duplicado con PR #11 |
| #4 A3 — DBI + notificaciones | ❌ No cubierto — lo tiene Jorge en PR #12 |

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
