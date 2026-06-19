# Elecmetal Innovacion

Plataforma conversacional para postulacion de iniciativas de innovacion.

## Arranque

Ver [`docs/context/CONTEXT.md`](docs/context/CONTEXT.md) — boot sequence de 12 pasos, desde infraestructura hasta produccion.

## Stack

| Componente | Tecnologia |
|------------|-----------|
| Frontend | Next.js 15+ (App Router, `src/`) |
| Backend | FastAPI (Python 3.11+) |
| Base de datos | PostgreSQL via Supabase |
| Autenticacion | Supabase Auth (Google OAuth, Magic Link) |
| Agentes IA | OpenAI GPT-4o (Custom GPTs) |
| Migraciones | Goose |

## Estructura

```
elecmetal-innovacion/
├── docs/context/          ← Modulo de contexto (leer primero)
├── frontend/              ← Next.js App Router
├── backend/               ← FastAPI
├── migrations/            ← Goose migrations
└── skills/                ← Prompts y skills de agentes IA
```
