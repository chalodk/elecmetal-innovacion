"""Clara — Asistente de postulacion de iniciativas ME Elecmetal.

Orquesta las llamadas a OpenAI GPT-4o para la agente conversacional Clara.
Carga el system prompt desde agent_configs en BD (fuente primaria), con
fallback a archivos de skill en disco. Streamea las respuestas token por
token via Server-Sent Events.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Resolucion de archivos de skill (fallback) ───────────────────────────────
# backend/app/services/clara.py  →  ../../../skills/
_SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"

_PROMPT_PATH = _SKILLS_DIR / "Clara_Prompt_v5_4_GPT.md"
_KB_PATH = _SKILLS_DIR / "Clara_KnowledgeBase_v5_9.md"

_MODEL = "gpt-4o"
_TEMPERATURE = 0.7


class ClaraService:
    """Servicio que encapsula la logica conversacional de Clara.

    El system prompt se carga de forma diferida desde agent_configs (BD)
    en el primer stream_response. Si la BD no tiene una config activa,
    se usan los archivos de skill en disco como fallback.
    """

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY no configurada")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._system_prompt: str | None = None
        self._prompt_loaded: bool = False

    async def _ensure_system_prompt(self) -> None:
        """Carga el system prompt desde agent_configs (BD) o fallback a archivos.

        Solo se ejecuta una vez — la primera llamada cachea el resultado.
        """
        if self._prompt_loaded:
            return

        prompt_text: str | None = None
        base_knowledge: str | None = None

        try:
            from app.core.database import get_pool

            pool = get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT prompt_text, base_knowledge "
                    "FROM agent_configs "
                    "WHERE agent_name = 'clara' AND is_active = true "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            if row:
                prompt_text = row["prompt_text"]
                base_knowledge = row["base_knowledge"]
                logger.info(
                    "clara.prompt loaded from agent_configs "
                    "prompt_len=%d kb_len=%s",
                    len(prompt_text or ""),
                    len(base_knowledge or ""),
                )
        except Exception as exc:
            logger.warning(
                "clara.prompt failed to load from agent_configs: %s — "
                "falling back to skill files",
                exc,
            )

        # ── Build system prompt ──────────────────────────────────────────
        if prompt_text:
            # BD is the primary source
            parts: list[str] = [prompt_text]

            # Append base_knowledge only if it's actual content, not just a
            # filename reference (e.g. "Base_de_Conocimiento_Clara.pdf").
            if base_knowledge and not base_knowledge.endswith(".pdf") and not base_knowledge.endswith(".skill"):
                parts.append("\n\n─── BASE DE CONOCIMIENTO ───\n\n")
                parts.append(base_knowledge)

            self._system_prompt = "".join(parts)
        else:
            # Fallback: load from skill files on disk
            logger.info("clara.prompt loading from skill files (fallback)")
            prompt = _PROMPT_PATH.read_text(encoding="utf-8")
            kb = _KB_PATH.read_text(encoding="utf-8")

            self._system_prompt = (
                f"{prompt}\n\n"
                f"─── BASE DE CONOCIMIENTO ───\n\n"
                f"{kb}\n\n"
                f"Usa la base de conocimiento como referencia para rubricas, "
                f"niveles TRL/CRL/BRL, y para generar el DBI final respetando "
                f"exactamente la plantilla documentada."
            )

        self._prompt_loaded = True

    async def stream_response(
        self,
        history: list[dict],
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """Genera chunks SSE con la respuesta de Clara.

        Args:
            history: Mensajes previos de la conversacion.
                     Cada dict tiene al menos {"role": "user"|"assistant", "content": "..."}
            user_id: ID del usuario (sub del JWT) para telemetria de OpenAI.

        Yields:
            Strings con formato SSE listas para StreamingResponse.
        """
        await self._ensure_system_prompt()

        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
        # Volcar historial previo (user + assistant, sin metadata)
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        try:
            stream = await self._client.chat.completions.create(
                model=_MODEL,
                messages=messages,
                temperature=_TEMPERATURE,
                stream=True,
                user=user_id,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    payload = json.dumps({"token": delta.content})
                    yield f"data: {payload}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as exc:
            error_payload = json.dumps({"error": str(exc)})
            yield f"data: {error_payload}\n\n"
