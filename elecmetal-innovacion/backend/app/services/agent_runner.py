"""
Agente IA runner — Streaming de respuestas desde OpenAI GPT-4o.

Cada agente (Clara, Analista, Evaluador) tiene su prompt versionado en
agent_configs. Este modulo carga el prompt activo, construye el contexto
de conversacion y streamea la respuesta token por token.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

import asyncpg
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import get_pool

logger = logging.getLogger(__name__)

# Cliente OpenAI unico (reutiliza connection pool interno)
_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def _load_agent_config(
    conn: asyncpg.Connection,
    agent_type: str,
) -> dict | None:
    """Carga la configuracion activa del agente desde agent_configs."""
    row = await conn.fetchrow(
        """
        SELECT agent_name, version, prompt_text, base_knowledge, skill_file
        FROM agent_configs
        WHERE agent_name = $1 AND is_active = true
        LIMIT 1
        """,
        agent_type,
    )
    if row is None:
        return None
    return dict(row)


async def _build_messages(
    conn: asyncpg.Connection,
    session_id: int,
    system_prompt: str,
) -> list[dict]:
    """Construye el array de mensajes para OpenAI: system prompt + historial."""
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    rows = await conn.fetch(
        """
        SELECT role, content
        FROM messages
        WHERE session_id = $1
        ORDER BY created_at ASC
        """,
        session_id,
    )

    for row in rows:
        messages.append({"role": row["role"], "content": row["content"]})

    return messages


async def stream_agent_response(
    session_id: int,
    agent_type: str = "clara",
) -> AsyncGenerator[str, None]:
    """Generador asincrono que streamea tokens desde OpenAI para una sesion.

    Args:
        session_id: ID de la sesion (para cargar historial de mensajes).
        agent_type: Tipo de agente ('clara', 'analista_oportunidad').

    Yields:
        Tokens de texto individuales (palabras, espacios, puntuacion).
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY no configurada — usando respuesta placeholder")
        placeholder = (
            "Clara no esta disponible por ahora. Intentaremos conectarla pronto. "
            "Mientras tanto, tu mensaje ha sido registrado."
        )
        # Tokenizar manualmente para simular streaming
        for word in placeholder.split(" "):
            if word:
                yield word + " "
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        # 1. Cargar config del agente
        config = await _load_agent_config(conn, agent_type)
        if config is None:
            logger.error("No active config for agent_type=%s", agent_type)
            yield "Lo siento, no encuentro mi configuracion. "
            yield "Por favor contacta al equipo de innovacion."
            return

        system_prompt = config["prompt_text"]
        logger.info(
            "agent_stream_start",
            agent=agent_type,
            version=config["version"],
            session_id=session_id,
        )

        # 2. Construir contexto de conversacion
        messages = await _build_messages(conn, session_id, system_prompt)

    # 3. Llamar a OpenAI con streaming (fuera del conn para no bloquear el pool)
    client = _get_openai_client()
    try:
        stream = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=2000,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    except Exception as exc:
        logger.error("openai_stream_error", error=str(exc), session_id=session_id)
        yield "\n\n[Error de conexion con Clara. Por favor intenta de nuevo.]"


async def persist_assistant_message(
    session_id: int,
    content: str,
) -> int:
    """Persiste el mensaje completo del asistente en la base de datos.

    Se llama despues de que el stream termina exitosamente.

    Returns:
        El ID del mensaje insertado.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages (session_id, role, content)
            VALUES ($1, 'assistant', $2)
            RETURNING id
            """,
            session_id,
            content,
        )
        return row["id"]
