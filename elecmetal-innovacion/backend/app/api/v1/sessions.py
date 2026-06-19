"""Sessions API — POST /, GET /, GET /{id}, GET /{id}/messages, POST /{id}/messages."""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_pool
from app.core.errors import AppError, ErrorCode
from app.core.pagination import (
    validate_cursor,
    validate_limit,
    paginated_response,
)
from app.core.security import (
    get_current_user,
    require_user_id,
    require_bigint_id,
)
from app.services.clara import ClaraService
from app.services.analista import AnalistaService
from app.services.dbi_persistence import detect_dbi_in_message, persist_initiative
from app.services.dbi_parser import DBIParseError

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Agent service singletons ────────────────────────────────────────────────

try:
    clara_service = ClaraService()
    logger.info("ClaraService initialized successfully")
except RuntimeError as exc:
    clara_service = None
    logger.warning("ClaraService not available: %s", exc)

try:
    analista_service = AnalistaService()
    logger.info("AnalistaService initialized successfully")
except RuntimeError as exc:
    analista_service = None
    logger.warning("AnalistaService not available: %s", exc)

_VALID_AGENT_TYPES = {"clara", "analista_oportunidad"}


# ── Request models ──────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    agent_type: str = "clara"
    title: str = "Nueva sesion"


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class UpdateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _dict_from_row(row: dict, include_user_id: bool = False) -> dict:
    """Converts a row dict to response dict."""
    result = {
        "id": row["id"],
        "agent_type": row.get("agent_type"),
        "status": row.get("status"),
        "title": row.get("title"),
        "created_at": row.get("created_at"),
    }
    if include_user_id:
        result["user_id"] = row.get("user_id")
    return result


# ── POST / ──────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    user: dict = Depends(get_current_user),
):
    """Crea una nueva sesion de chat con un agente IA."""
    user_id = require_user_id(user)

    if body.agent_type not in _VALID_AGENT_TYPES:
        raise AppError(
            code=ErrorCode.INVALID_AGENT_TYPE,
            message=f"agent_type debe ser uno de: {', '.join(sorted(_VALID_AGENT_TYPES))}",
            details={"field": "agent_type", "value": body.agent_type},
        )

    escaped_title = body.title.replace("'", "''")
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO sessions (user_id, agent_type, status, title) "
            f"VALUES ('{user_id}', '{body.agent_type}', 'active', '{escaped_title}') "
            f"RETURNING *"
        )

    return _dict_from_row(row, include_user_id=True)


# ── GET / ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_sessions(
    user: dict = Depends(get_current_user),
    cursor: str | None = Query(None, description="Cursor for pagination (session id)"),
    limit: str | None = Query(None, description=f"Page size (max {100})"),
    agent_filter: str | None = Query(None, description="Filter by agent_type"),
):
    """Lista las sesiones activas del usuario autenticado con paginacion."""
    user_id = require_user_id(user)

    cursor_val = validate_cursor(cursor)
    page_limit = validate_limit(limit)

    conditions = [f"user_id = '{user_id}'", "status = 'active'"]

    if agent_filter and agent_filter in _VALID_AGENT_TYPES:
        conditions.append(f"agent_type = '{agent_filter}'")

    if cursor_val is not None:
        conditions.append(f"id < {cursor_val}")

    where_clause = "WHERE " + " AND ".join(conditions)

    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM sessions "
            f"{where_clause} "
            f"ORDER BY created_at DESC "
            f"LIMIT {page_limit + 1}"
        )

    return paginated_response(
        [_dict_from_row(r, include_user_id=True) for r in rows],
        cursor_field="id",
        limit=page_limit,
    )


# ── GET /{id} ──────────────────────────────────────────────────────────────

@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Obtiene una sesion con metadata extendida."""
    user_id = require_user_id(user)
    sid = require_bigint_id(session_id, "session_id")

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM sessions "
            f"WHERE id = {sid} AND user_id = '{user_id}'"
        )
        if not row:
            raise AppError(
                code=ErrorCode.NOT_FOUND,
                message="Sesion no encontrada",
            )

        msg_count = await conn.fetchval(
            f"SELECT count(*) FROM messages WHERE session_id = {sid}"
        )

    result = _dict_from_row(row, include_user_id=True)
    result["started_at"] = row.get("started_at")
    result["ended_at"] = row.get("ended_at")
    result["updated_at"] = row.get("updated_at")
    result["message_count"] = msg_count

    return result


# ── GET /{id}/messages ──────────────────────────────────────────────────────

@router.get("/{session_id}/messages")
async def get_messages(
    session_id: str,
    user: dict = Depends(get_current_user),
    cursor: str | None = Query(None, description="Cursor for pagination (message id)"),
    limit: str | None = Query(None, description=f"Page size (max {100})"),
):
    """Obtiene el historial de mensajes de una sesion con paginacion cursor."""
    user_id = require_user_id(user)
    sid = require_bigint_id(session_id, "session_id")

    cursor_val = validate_cursor(cursor)
    page_limit = validate_limit(limit)

    pool = get_pool()
    async with pool.acquire() as conn:
        # Verify session exists and belongs to user
        session_row = await conn.fetchrow(
            f"SELECT id FROM sessions "
            f"WHERE id = {sid} AND user_id = '{user_id}'"
        )
        if not session_row:
            raise AppError(
                code=ErrorCode.NOT_FOUND,
                message="Sesion no encontrada",
            )

        conditions = [f"session_id = {sid}"]
        if cursor_val is not None:
            conditions.append(f"id > {cursor_val}")

        where_clause = "WHERE " + " AND ".join(conditions)

        rows = await conn.fetch(
            f"SELECT id, session_id, role, content, metadata, created_at "
            f"FROM messages "
            f"{where_clause} "
            f"ORDER BY created_at ASC, id ASC "
            f"LIMIT {page_limit + 1}"
        )

    return paginated_response(
        [dict(r) for r in rows],
        cursor_field="id",
        limit=page_limit,
    )


# ── POST /{id}/messages ─────────────────────────────────────────────────────

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


async def _persist_assistant_message(
    session_id: str, content: str
) -> int:
    """Inserta el mensaje del asistente en la BD y devuelve su ID."""
    pool = get_pool()
    async with pool.acquire() as conn:
        escaped = content.replace("'", "''")
        row = await conn.fetchrow(
            f"INSERT INTO messages (session_id, role, content) "
            f"VALUES ({session_id}, 'assistant', '{escaped}') "
            f"RETURNING id"
        )
    return row["id"]


async def _stream_agent_response(
    session_id: str,
    user_id: str,
    history: list[dict],
    agent_type: str,
) -> AsyncGenerator[str, None]:
    """SSE generator: stream agent tokens, persist response, detect DBI (Clara only)."""
    full_response: list[str] = []

    if agent_type == "analista_oportunidad":
        service = analista_service
    else:
        service = clara_service

    if service is None:
        async for chunk in _stream_placeholder(session_id):
            yield chunk
        return

    try:
        async for chunk in service.stream_response(history, user_id):
            line = chunk.strip()

            if line == "data: [DONE]":
                content = "".join(full_response)
                asst_msg_id = await _persist_assistant_message(
                    session_id, content
                )

                # ── DBI detection (Clara only) ─────────────────────────
                initiative_info = None
                if agent_type == "clara" and detect_dbi_in_message(content):
                    logger.info("DBI detected in assistant message, attempting persistence")
                    try:
                        initiative = await persist_initiative(
                            session_id=int(session_id),
                            user_id=user_id,
                            dbi_text=content,
                        )
                        initiative_info = {
                            "initiative_id": initiative["id"],
                            "initiative_code": initiative["initiative_code"],
                            "status": initiative["status"],
                        }
                        logger.info(
                            "dbi.persisted initiative_id=%s initiative_code=%s",
                            initiative["id"], initiative["initiative_code"],
                        )
                    except DBIParseError as pe:
                        logger.warning("DBI parse failed: %s", pe)
                        initiative_info = {"parse_error": str(pe)}
                    except Exception as pe_exc:
                        logger.exception("DBI persistence failed")
                        initiative_info = {"persistence_error": str(pe_exc)}

                done_payload: dict = {"done": True, "message_id": asst_msg_id}
                if initiative_info:
                    done_payload["initiative"] = initiative_info
                yield f"data: {json.dumps(done_payload)}\n\n"
            else:
                try:
                    payload_str = line.removeprefix("data: ")
                    payload = json.loads(payload_str)
                    if "token" in payload:
                        full_response.append(payload["token"])
                except (json.JSONDecodeError, KeyError):
                    pass
                yield chunk

    except Exception as exc:
        logger.exception("Error streaming agent response")
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"


async def _stream_placeholder(
    session_id: str,
) -> AsyncGenerator[str, None]:
    """SSE fallback when Clara is unavailable."""
    PLACEHOLDER = (
        "Clara no esta disponible en este momento. "
        "Intentaremos conectarla pronto."
    )
    words = PLACEHOLDER.split(" ")
    for i, word in enumerate(words):
        token = word + (" " if i < len(words) - 1 else "")
        yield f"data: {json.dumps({'token': token})}\n\n"

    asst_msg_id = await _persist_assistant_message(session_id, PLACEHOLDER)
    yield f"data: {json.dumps({'done': True, 'message_id': asst_msg_id})}\n\n"


@router.post("/{session_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
):
    """Envia un mensaje en una sesion y streamea la respuesta de Clara via SSE."""
    user_id = require_user_id(user)
    sid = require_bigint_id(session_id, "session_id")

    pool = get_pool()
    async with pool.acquire() as conn:
        session_row = await conn.fetchrow(
            f"SELECT id, agent_type FROM sessions "
            f"WHERE id = {sid} AND user_id = '{user_id}'"
        )
        if not session_row:
            raise AppError(
                code=ErrorCode.NOT_FOUND,
                message="Sesion no encontrada",
            )

        agent_type = session_row["agent_type"]

        escaped_content = body.content.replace("'", "''")
        await conn.execute(
            f"INSERT INTO messages (session_id, role, content) "
            f"VALUES ({sid}, 'user', '{escaped_content}')"
        )

        rows = await conn.fetch(
            f"SELECT role, content FROM messages "
            f"WHERE session_id = {sid} "
            f"ORDER BY created_at ASC"
        )

    history = [{"role": r["role"], "content": r["content"]} for r in rows]

    generator = _stream_agent_response(str(sid), user_id, history, agent_type)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
