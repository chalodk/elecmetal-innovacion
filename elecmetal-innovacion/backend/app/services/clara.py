"""Clara — Asistente de postulacion de iniciativas ME Elecmetal.

Orquesta las llamadas a OpenAI GPT-4o para la agente conversacional Clara.
Carga el prompt del sistema desde los archivos de skill en disco y streamea
las respuestas token por token via Server-Sent Events.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import settings

# ── Resolucion de archivos de skill ──────────────────────────────────────────
# backend/app/services/clara.py  →  ../../../skills/
_SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"

_PROMPT_PATH = _SKILLS_DIR / "Clara_Prompt_v5_4_GPT.md"
_KB_PATH = _SKILLS_DIR / "Clara_KnowledgeBase_v5_9.md"

_MODEL = "gpt-4o"
_TEMPERATURE = 0.7


def _load_skill(path: Path) -> str:
    """Lee un archivo de skill desde disco. Lanza RuntimeError si no existe."""
    if not path.exists():
        raise RuntimeError(f"Skill file not found: {path}")
    return path.read_text(encoding="utf-8")


def _build_system_prompt() -> str:
    """Construye el mensaje de sistema combinando prompt + knowledge base."""
    prompt = _load_skill(_PROMPT_PATH)
    kb = _load_skill(_KB_PATH)

    return (
        f"{prompt}\n\n"
        f"─── BASE DE CONOCIMIENTO ───\n\n"
        f"{kb}\n\n"
        f"Usa la base de conocimiento como referencia para rubricas, "
        f"niveles TRL/CRL/BRL, y para generar el DBI final respetando "
        f"exactamente la plantilla documentada."
    )


class ClaraService:
    """Servicio que encapsula la logica conversacional de Clara."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY no configurada")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._system_prompt = _build_system_prompt()

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
