"""Analista de Oportunidad — TAM/SAM/SOM modeler (Step 11 of the boot sequence).

Orchestrates OpenAI GPT-4o calls for the Analista de Oportunidad agent.
Loads the system prompt from skills/prompt_analista_oportunidad_v2.md.

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
from pathlib import Path
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import settings

# ── Skill file resolution ──────────────────────────────────────────────────
_SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"

_PROMPT_PATH = _SKILLS_DIR / "prompt_analista_oportunidad_v2.md"

_MODEL = "gpt-4o"
_TEMPERATURE = 0.7


def _load_skill(path: Path) -> str:
    """Lee un archivo de skill desde disco. Lanza RuntimeError si no existe."""
    if not path.exists():
        raise RuntimeError(f"Skill file not found: {path}")
    return path.read_text(encoding="utf-8")


def _build_system_prompt() -> str:
    """Construye el mensaje de sistema desde el prompt v2."""
    prompt = _load_skill(_PROMPT_PATH)

    return (
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


class AnalistaService:
    """Servicio que encapsula la logica conversacional del Analista."""

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
        """Genera chunks SSE con la respuesta del Analista.

        Args:
            history: Mensajes previos de la conversacion.
            user_id: ID del usuario para telemetria de OpenAI.

        Yields:
            Strings con formato SSE listas para StreamingResponse.
        """
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
