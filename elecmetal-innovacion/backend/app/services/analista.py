"""Analista de Oportunidad — TAM/SAM/SOM modeler (Step 11 of the boot sequence).

Orchestrates OpenAI GPT-4o calls for the Analista de Oportunidad agent.
Carga el system prompt desde agent_configs en BD (fuente primaria), con
fallback a archivos de skill en disco. Streamea las respuestas token por
token via Server-Sent Events.

The Analista executes a 12-state machine (A-L):
  A — INGESTA: read 6 input fields
  B — CHECKPOINT: understanding validation
  C — SETUP: geography, payer, monetization
  D — MODEL SELECTION: propose 1-2 templates
  E — COMPONENTS: data/assumption/derived map
  F — DATA: source-cited data
  G — ASSUMPTIONS: ranges + rationale
  H — CALCULATION: TAM/SAM/SOM
  I — SENSITIVITY: critical assumption
  J — SCENARIOS: base/neg/pos
  K — OUTPUTS: data row + narrative + slide-ready
  L — ITERATION: diff + confirmation

Output labels: DATO, SUPUESTO, DERIVADO.
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
# backend/app/services/analista.py  →  ../../../skills/
_SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"

_PROMPT_PATH = _SKILLS_DIR / "prompt_analista_oportunidad_v2.md"

_MODEL = "gpt-4o"
_TEMPERATURE = 0.7


class AnalistaService:
    """Servicio que encapsula la logica conversacional del Analista.

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

        try:
            from app.core.database import get_pool

            pool = get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT prompt_text, base_knowledge "
                    "FROM agent_configs "
                    "WHERE agent_name = 'analista_oportunidad' AND is_active = true "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            if row:
                prompt_text = row["prompt_text"]
                logger.info(
                    "analista.prompt loaded from agent_configs prompt_len=%d",
                    len(prompt_text or ""),
                )
        except Exception as exc:
            logger.warning(
                "analista.prompt failed to load from agent_configs: %s — "
                "falling back to skill files",
                exc,
            )

        # ── Build system prompt ──────────────────────────────────────────
        if prompt_text:
            self._system_prompt = prompt_text
        else:
            # Fallback: load from skill file on disk
            logger.info("analista.prompt loading from skill file (fallback)")
            prompt = _PROMPT_PATH.read_text(encoding="utf-8")

            self._system_prompt = (
                f"{prompt}\n\n"
                f"─── INSTRUCCIONES ADICIONALES ───\n\n"
                f"Eres el Analista de Oportunidad Economica de ME Elecmetal. "
                f"Sigue ESTRICTAMENTE la maquina de estados A-L documentada arriba. "
                f"Nunca saltes estados. Al entrar a cada estado, explica en una frase "
                f"que van a hacer juntos.\n\n"
                f"IMPORTANTE: Todo numero que entregues DEBE estar etiquetado como "
                f"DATO, SUPUESTO o DERIVADO. Sin excepciones.\n"
                f"Si el usuario te corrige algo, itera (estado L) describiendo el 'diff' "
                f"antes de recalcular.\n"
                f"Geografia: UNA sola por calculo. Horizonte: Ano 5. Moneda: USD nominal."
            )

        self._prompt_loaded = True

    async def stream_response(
        self,
        history: list[dict],
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """Genera chunks SSE con la respuesta del Analista.

        Args:
            history: Mensajes previos de la conversacion.
            user_id: ID del usuario para telemetria de OpenAI.

        Yields:
            Strings con formato SSE listas para StreamingResponse.
        """
        await self._ensure_system_prompt()

        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
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
