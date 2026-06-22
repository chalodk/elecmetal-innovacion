import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_pool
from app.core.security import get_current_user

router = APIRouter()


class CreateSessionRequest(BaseModel):
    agent_type: str = Field(..., pattern="^(clara|analista_oportunidad)$")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


@router.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    """Lista las sesiones del usuario autenticado, ordenadas por mas reciente."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id::text, agent_type, status, title,
                   started_at, ended_at, created_at, updated_at
            FROM sessions
            WHERE user_id = $1::uuid
            ORDER BY created_at DESC
            """,
            user["sub"],
        )

    return {
        "data": [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "agent_type": row["agent_type"],
                "status": row["status"],
                "title": row["title"],
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ]
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    user: dict = Depends(get_current_user),
):
    """Crea una nueva sesion de chat con un agente IA."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id, agent_type, status)
            VALUES ($1::uuid, $2, 'active')
            RETURNING id, user_id::text, agent_type, status, title,
                      started_at, ended_at, created_at, updated_at
            """,
            user["sub"],
            body.agent_type,
        )

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "agent_type": row["agent_type"],
        "status": row["status"],
        "title": row["title"],
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    """Obtiene una sesion por ID. Solo el dueno puede verla."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id::text, agent_type, status, title,
                   started_at, ended_at, created_at, updated_at
            FROM sessions
            WHERE id = $1
            """,
            session_id,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "La sesion no existe",
                }
            },
        )

    if row["user_id"] != user["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "No tienes acceso a esta sesion",
                }
            },
        )

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "agent_type": row["agent_type"],
        "status": row["status"],
        "title": row["title"],
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: int,
    cursor: int | None = Query(default=None, gt=0, description="ID del ultimo mensaje de la pagina anterior"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximo de mensajes por pagina"),
    user: dict = Depends(get_current_user),
):
    """Pagina los mensajes de una sesion. Solo el dueno puede verlos."""
    pool = get_pool()
    async with pool.acquire() as conn:
        # Validar ownership
        owner = await conn.fetchrow(
            "SELECT user_id::text FROM sessions WHERE id = $1",
            session_id,
        )

    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "La sesion no existe",
                }
            },
        )

    if owner["user_id"] != user["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "No tienes acceso a esta sesion",
                }
            },
        )

    async with pool.acquire() as conn:
        if cursor is not None:
            rows = await conn.fetch(
                """
                SELECT id, session_id, role, content, metadata, created_at
                FROM messages
                WHERE session_id = $1 AND id > $2
                ORDER BY created_at ASC
                LIMIT $3
                """,
                session_id,
                cursor,
                limit + 1,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, session_id, role, content, metadata, created_at
                FROM messages
                WHERE session_id = $1
                ORDER BY created_at ASC
                LIMIT $2
                """,
                session_id,
                limit + 1,
            )

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    data = [
        {
            "id": row["id"],
            "session_id": row["session_id"],
            "role": row["role"],
            "content": row["content"],
            "metadata": row["metadata"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]

    return {
        "data": data,
        "pagination": {
            "next_cursor": data[-1]["id"] if data else None,
            "has_more": has_more,
        },
    }


@router.post("/sessions/{session_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    session_id: int,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
):
    """Envia un mensaje del usuario a la sesion.

    Solo persiste el user_message. La respuesta del asistente se streamea
    via GET /sessions/{id}/stream y se persiste al completar el stream.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        # Validar sesion: existe, ownership, activa
        session = await conn.fetchrow(
            "SELECT id, user_id::text, status FROM sessions WHERE id = $1",
            session_id,
        )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "La sesion no existe",
                }
            },
        )

    if session["user_id"] != user["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "No tienes acceso a esta sesion",
                }
            },
        )

    if session["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SESSION_NOT_ACTIVE",
                    "message": "La sesion esta cerrada. No se pueden enviar nuevos mensajes.",
                }
            },
        )

    async with pool.acquire() as conn:
        user_msg = await conn.fetchrow(
            """
            INSERT INTO messages (session_id, role, content)
            VALUES ($1, 'user', $2)
            RETURNING id, session_id, role, content, metadata, created_at
            """,
            session_id,
            body.content,
        )

    return {
        "user_message": {
            "id": user_msg["id"],
            "session_id": user_msg["session_id"],
            "role": user_msg["role"],
            "content": user_msg["content"],
            "metadata": user_msg["metadata"],
            "created_at": user_msg["created_at"].isoformat() if user_msg["created_at"] else None,
        },
    }


# ─── SSE Streaming ──────────────────────────────────────────────────────────


async def _sse_event_generator(
    session_id: int,
    agent_type: str,
    resume_from: int = 0,
):
    """Generador asincrono que emite tokens desde OpenAI via SSE.

    Formato: data: {"token":"..."} + data: [DONE].
    Respeta resume_from para reconexiones: omite los primeros N tokens.
    Al completar el stream, persiste el mensaje completo del asistente en DB.
    """
    from app.services.agent_runner import (
        stream_agent_response,
        persist_assistant_message,
    )

    accumulated: list[str] = []
    token_index = 0

    try:
        async for token in stream_agent_response(session_id, agent_type):
            accumulated.append(token)
            if token_index >= resume_from:
                payload = json.dumps({"token": token}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            token_index += 1

        # Persistir el mensaje completo del asistente
        full_content = "".join(accumulated)
        if full_content.strip():
            try:
                await persist_assistant_message(session_id, full_content)
            except Exception:
                # Error persistiendo no debe romper el stream
                pass

    except Exception:
        # Error inesperado — notificar al frontend
        error_token = json.dumps(
            {"token": "\n\n[Error inesperado. Por favor intenta de nuevo.]"},
            ensure_ascii=False,
        )
        yield f"data: {error_token}\n\n"

    yield "data: [DONE]\n\n"


@router.get("/sessions/{session_id}/stream")
async def stream_response(
    session_id: int,
    resume_from: int | None = Query(
        default=None,
        ge=0,
        description="Cantidad de tokens ya recibidos para reconexion",
    ),
    user: dict = Depends(get_current_user),
):
    """SSE stream de la respuesta del asistente via OpenAI.

    El frontend (B2) espera este endpoint con formato:
      data: {"token":"Hola"}
      data: {"token":" mundo"}
      data: [DONE]

    Soporta ?resume_from=N para reconexion automatica tras corte del stream.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            "SELECT id, user_id::text, status, agent_type FROM sessions WHERE id = $1",
            session_id,
        )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "La sesion no existe",
                }
            },
        )

    if session["user_id"] != user["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "No tienes acceso a esta sesion",
                }
            },
        )

    if session["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SESSION_NOT_ACTIVE",
                    "message": "La sesion esta cerrada. No se puede streamear.",
                }
            },
        )

    start_from = resume_from if resume_from is not None else 0

    return StreamingResponse(
        _sse_event_generator(
            session_id,
            agent_type=session["agent_type"],
            resume_from=start_from,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
