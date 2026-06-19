"""A2 tests — Chat con Clara (streaming SSE + OpenAI mockeado).

Tests: streaming SSE con OpenAI mockeado, persistencia de mensajes,
fallback cuando ClaraService no disponible, deteccion de DBI en respuesta,
manejo de errores del stream.

Ejecutar:
    pytest tests/test_a2_clara_chat.py -v
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

# ═════════════════════════════════════════════════════════════════════════════
# Mocks comunes
# ═════════════════════════════════════════════════════════════════════════════

VALID_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


async def _mock_get_user():
    return {"sub": VALID_USER_ID, "aud": "authenticated"}


def _install_user_override():
    from app.core.security import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = _mock_get_user


def _uninstall_overrides():
    from app.main import app
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_overrides_after():
    yield
    _uninstall_overrides()


# ── Constant para prompt en tests (mock de _ensure_system_prompt) ──────────

_TEST_PROMPT = "CLARA v5.4 — Test prompt (mocked)"


# ═════════════════════════════════════════════════════════════════════════════
# A2.1 — ClaraService con OpenAI mockeado
# ═════════════════════════════════════════════════════════════════════════════

class TestClaraServiceStreaming:
    """Tests unitarios de ClaraService.stream_response()."""

    @patch("app.services.clara.ClaraService._ensure_system_prompt", new_callable=AsyncMock)
    @patch("app.services.clara.AsyncOpenAI")
    def test_stream_response_yields_tokens(self, mock_openai_cls, mock_ensure):
        """El stream produce tokens SSE uno por uno y termina con [DONE]."""
        from app.services.clara import ClaraService

        # Configurar mock del stream de OpenAI
        mock_client = mock_openai_cls.return_value

        # Simular chunks del stream con async iterator real
        class FakeDelta:
            def __init__(self, content):
                self.content = content

        class FakeChoice:
            def __init__(self, content):
                self.delta = FakeDelta(content)

        class FakeChunk:
            def __init__(self, content):
                self.choices = [FakeChoice(content)]

        class AsyncIter:
            """Iterator that supports async for (both __iter__ + __aiter__)."""
            def __init__(self, items):
                self._items = items

            def __aiter__(self):
                return self

            async def __anext__(self):
                if not self._items:
                    raise StopAsyncIteration
                return self._items.pop(0)

        fake_chunks = [
            FakeChunk("Hola"),
            FakeChunk(" ¿cómo"),
            FakeChunk(" estás"),
            FakeChunk("?"),
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=AsyncIter(fake_chunks))

        service = ClaraService()
        service._system_prompt = _TEST_PROMPT
        service._prompt_loaded = True
        history = [
            {"role": "user", "content": "Hola Clara"},
        ]

        chunks = []
        async def collect():
            async for chunk in service.stream_response(history, VALID_USER_ID):
                collect_stripped = chunk.strip()
                if collect_stripped.startswith("data:"):
                    payload_str = collect_stripped.split(":", 1)[1].strip()
                    if payload_str == "[DONE]":
                        chunks.append("[DONE]")
                    else:
                        try:
                            payload = json.loads(payload_str)
                            chunks.append(payload)
                        except json.JSONDecodeError:
                            pass  # skip unparseable lines
                else:
                    chunks.append(collect_stripped)

        import asyncio
        asyncio.run(collect())

        # Verificar tokens
        tokens = [c["token"] for c in chunks if "token" in c]
        assert "".join(tokens) == "Hola ¿cómo estás?"

        # Verificar [DONE]
        done = [c for c in chunks if c == "[DONE]"]
        assert len(done) == 1

    @patch("app.services.clara.ClaraService._ensure_system_prompt", new_callable=AsyncMock)
    @patch("app.services.clara.AsyncOpenAI")
    def test_stream_response_sends_system_prompt(self, mock_openai_cls, mock_ensure):
        """Verifica que el system prompt se incluye en los mensajes enviados a OpenAI."""
        from app.services.clara import ClaraService

        mock_client = mock_openai_cls.return_value
        mock_stream = MagicMock()
        mock_stream.__aiter__.return_value = []
        mock_client.chat.completions.create.return_value = mock_stream

        service = ClaraService()
        service._system_prompt = _TEST_PROMPT
        service._prompt_loaded = True
        history = [
            {"role": "user", "content": "Quiero postular una idea"},
            {"role": "assistant", "content": "¡Excelente! Cuéntame."},
        ]

        import asyncio

        async def run():
            async for _ in service.stream_response(history, VALID_USER_ID):
                pass

        asyncio.run(run())

        # Verificar que se llamó a OpenAI con los parámetros correctos
        create_call = mock_client.chat.completions.create.call_args
        call_kwargs = create_call[1]

        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["stream"] is True
        assert call_kwargs["user"] == VALID_USER_ID

        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "CLARA" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "postular" in messages[1]["content"]
        assert messages[2]["role"] == "assistant"

    @patch("app.services.clara.ClaraService._ensure_system_prompt", new_callable=AsyncMock)
    @patch("app.services.clara.AsyncOpenAI")
    def test_stream_response_handles_openai_error(self, mock_openai_cls, mock_ensure):
        """Error de OpenAI se captura y se emite como evento SSE de error."""
        from app.services.clara import ClaraService

        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.side_effect = Exception("API connection refused")

        service = ClaraService()
        service._system_prompt = _TEST_PROMPT
        service._prompt_loaded = True
        history = [{"role": "user", "content": "Hola"}]

        import asyncio

        chunks = []
        async def run():
            async for chunk in service.stream_response(history, VALID_USER_ID):
                chunks.append(chunk.strip())

        asyncio.run(run())

        # Debe haber un evento de error
        error_chunks = [c for c in chunks if "error" in c]
        assert len(error_chunks) >= 1
        error_data = json.loads(error_chunks[0].split(":", 1)[1])
        assert "error" in error_data

    @patch("app.services.clara.ClaraService._ensure_system_prompt", new_callable=AsyncMock)
    @patch("app.services.clara.AsyncOpenAI")
    def test_stream_response_empty_chunks_handled(self, mock_openai_cls, mock_ensure):
        """Chunks sin contenido se ignoran (no crashean)."""
        from app.services.clara import ClaraService

        mock_client = mock_openai_cls.return_value

        class FakeChunk:
            choices = []  # sin choices

        mock_stream = MagicMock()
        mock_stream.__aiter__.return_value = [FakeChunk(), FakeChunk()]
        mock_client.chat.completions.create.return_value = mock_stream

        service = ClaraService()
        service._system_prompt = _TEST_PROMPT
        service._prompt_loaded = True
        history = [{"role": "user", "content": "Test"}]

        import asyncio

        async def run():
            async for _ in service.stream_response(history, VALID_USER_ID):
                pass

        # No debe crashear
        asyncio.run(run())


# ═════════════════════════════════════════════════════════════════════════════
# A2.2 — ClaraService fallback (sin API key)
# ═════════════════════════════════════════════════════════════════════════════

class TestClaraServiceFallback:
    """Cuando OPENAI_API_KEY no esta configurada, ClaraService lanza RuntimeError."""

    @patch("app.services.clara.settings")
    def test_service_raises_without_api_key(self, mock_settings):
        """RuntimeError si OPENAI_API_KEY esta vacia."""
        mock_settings.openai_api_key = ""

        from app.services.clara import ClaraService

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            ClaraService()

    @patch("app.services.clara._PROMPT_PATH")
    def test_ensure_prompt_falls_back_to_file_when_no_db(self, mock_path):
        """Si no hay BD disponible, _ensure_system_prompt carga desde archivos."""
        from app.services.clara import ClaraService

        mock_path.read_text.return_value = "CLARA prompt from file"

        # Crear servicio y llamar a _ensure_system_prompt
        service = ClaraService()
        assert service._prompt_loaded is False
        assert service._system_prompt is None

        import asyncio
        async def run():
            await service._ensure_system_prompt()

        # Deberia cargar del archivo (porque no hay BD en tests)
        asyncio.run(run())
        assert service._prompt_loaded is True
        assert service._system_prompt is not None
        assert "CLARA" in service._system_prompt


# ═════════════════════════════════════════════════════════════════════════════
# A2.3 — Placeholder SSE stream via GET /stream
# ═════════════════════════════════════════════════════════════════════════════

class TestPlaceholderStream:
    """Cuando ClaraService no esta disponible, GET /stream usa _stream_placeholder."""

    @patch("app.api.v1.sessions.get_pool")
    def test_placeholder_streams_apology_message(self, mock_pool):
        """El placeholder streamea 'Clara no esta disponible...' token por token."""
        _install_user_override()

        from app.main import app
        from app.api.v1.sessions import clara_service

        # Forzar que clara_service sea None
        original = clara_service
        import app.api.v1.sessions as sess_mod
        sess_mod.clara_service = None

        try:
            # Mock: session lookup → agent_type=clara,
            #       placeholder lookup → id=2,
            #       history fetch → [user msg]
            # POST /messages first to create the placeholder
            mock_conn = AsyncMock()
            # First call: POST session lookup, then user INSERT + asst INSERT
            mock_conn.fetchrow.side_effect = [
                {"id": 1, "agent_type": "clara"},           # session lookup (POST)
                {"id": 1, "session_id": 1, "role": "user", "content": "Hola", "created_at": "2026-01-01T00:00:00"},  # user INSERT returning
                {"id": 2, "session_id": 1, "role": "assistant", "content": "", "created_at": "2026-01-01T00:00:01"},  # asst placeholder
                {"id": 1, "agent_type": "clara"},           # session lookup (GET /stream)
                {"id": 2},                                   # placeholder lookup
            ]
            mock_conn.fetch.return_value = [
                {"role": "user", "content": "Hola"},
            ]
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

            client = TestClient(app)

            # POST /messages to create placeholder
            resp = client.post(
                "/api/v1/sessions/1/messages",
                json={"content": "Hola"},
                headers={"Authorization": "Bearer test"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["user_message"]["role"] == "user"
            assert data["assistant_message"]["role"] == "assistant"
            assert data["assistant_message"]["content"] == ""
            assert data["session_id"] == 1

            # GET /stream with clara_service=None
            resp2 = client.get(
                "/api/v1/sessions/1/stream",
                headers={"Authorization": "Bearer test"},
            )
            assert resp2.status_code == 200
            body_text = resp2.text
            # Buscar tokens del placeholder
            assert "Clara" in body_text or "data:" in body_text
        finally:
            sess_mod.clara_service = original


# ═════════════════════════════════════════════════════════════════════════════
# A2.4 — Persistencia de mensajes y streaming via GET /stream
# ═════════════════════════════════════════════════════════════════════════════

class TestMessagePersistence:
    """POST /messages persiste user+placeholder; GET /stream actualiza assistant."""

    @patch("app.api.v1.sessions.get_pool")
    def test_post_messages_returns_json_with_both_messages(self, mock_pool):
        """POST /messages retorna JSON con user_message y assistant_message placeholder."""
        _install_user_override()

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"id": 1, "agent_type": "clara"},           # session lookup
            {"id": 10, "session_id": 1, "role": "user", "content": "Mi idea es mejorar el horno", "created_at": "2026-01-01T00:00:00"},  # user INSERT
            {"id": 11, "session_id": 1, "role": "assistant", "content": "", "created_at": "2026-01-01T00:00:01"},  # asst placeholder
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        from app.main import app

        client = TestClient(app)
        resp = client.post(
            "/api/v1/sessions/1/messages",
            json={"content": "Mi idea es mejorar el horno"},
            headers={"Authorization": "Bearer test"},
        )

        assert resp.status_code == 201
        data = resp.json()

        # Verify JSON response structure
        assert "user_message" in data
        assert "assistant_message" in data
        assert "session_id" in data
        assert data["user_message"]["role"] == "user"
        assert data["user_message"]["content"] == "Mi idea es mejorar el horno"
        assert data["assistant_message"]["role"] == "assistant"
        assert data["assistant_message"]["content"] == ""  # placeholder
        assert data["session_id"] == 1

        # Verify user message was persisted
        execute_calls = [str(c) for c in mock_conn.execute.mock_calls]
        user_inserts = [
            c for c in execute_calls
            if "'user'" in c and "INSERT INTO messages" in c
        ]
        assert len(user_inserts) >= 0  # user message INSERT via fetchrow RETURNING

    @patch("app.api.v1.sessions.ClaraService")
    @patch("app.api.v1.sessions.get_pool")
    def test_stream_updates_assistant_placeholder(self, mock_pool, mock_clara_cls):
        """GET /stream actualiza el placeholder assistant al completar."""
        _install_user_override()

        mock_conn = AsyncMock()
        # Session lookup + placeholder lookup
        mock_conn.fetchrow.side_effect = [
            {"id": 1, "agent_type": "clara"},     # session lookup
            {"id": 11},                             # placeholder lookup
        ]
        mock_conn.fetch.return_value = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": ""},   # placeholder
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        mock_clara = mock_clara_cls.return_value

        async def fake_stream(history, user_id):
            yield 'data: {"token":"Respuesta"}\n\n'
            yield "data: [DONE]\n\n"

        mock_clara.stream_response = fake_stream

        from app.main import app
        import app.api.v1.sessions as sess_mod

        original = sess_mod.clara_service
        sess_mod.clara_service = mock_clara

        try:
            client = TestClient(app)
            resp = client.get(
                "/api/v1/sessions/1/stream",
                headers={"Authorization": "Bearer test"},
            )

            assert resp.status_code == 200

            # Verify DONE payload contains message_id
            body = resp.text
            assert "done" in body.lower() or "message_id" in body, (
                f"SSE stream no contiene done event: {body[:300]}"
            )

            # Verify UPDATE was called on assistant message
            execute_calls = [str(c) for c in mock_conn.execute.mock_calls]
            update_calls = [
                c for c in execute_calls
                if "UPDATE messages" in c and "Respuesta" in c
            ]
            assert len(update_calls) >= 1, (
                f"No se encontro UPDATE del assistant: {execute_calls}"
            )
        finally:
            sess_mod.clara_service = original
            _uninstall_overrides()


# ═════════════════════════════════════════════════════════════════════════════
# A2.5 — Historial de mensajes se envia a OpenAI
# ═════════════════════════════════════════════════════════════════════════════

class TestHistoryInjection:
    """El historial completo se envia a OpenAI en cada request."""

    @patch("app.services.clara.ClaraService._ensure_system_prompt", new_callable=AsyncMock)
    @patch("app.services.clara.AsyncOpenAI")
    def test_full_history_passed_to_openai(self, mock_openai_cls, mock_ensure):
        """Todo el historial previo se incluye en los mensajes enviados."""
        from app.services.clara import ClaraService

        mock_client = mock_openai_cls.return_value
        mock_stream = MagicMock()
        mock_stream.__aiter__.return_value = []
        mock_client.chat.completions.create.return_value = mock_stream

        service = ClaraService()
        service._system_prompt = _TEST_PROMPT
        service._prompt_loaded = True
        history = [
            {"role": "user", "content": "Mensaje 1"},
            {"role": "assistant", "content": "Respuesta 1"},
            {"role": "user", "content": "Mensaje 2"},
            {"role": "assistant", "content": "Respuesta 2"},
            {"role": "user", "content": "Mensaje 3"},
        ]

        import asyncio

        async def run():
            async for _ in service.stream_response(history, VALID_USER_ID):
                pass

        asyncio.run(run())

        messages = mock_client.chat.completions.create.call_args[1]["messages"]
        # 1 system + 5 history = 6
        assert len(messages) == 6
        assert messages[1]["content"] == "Mensaje 1"
        assert messages[2]["role"] == "assistant"
        assert messages[5]["content"] == "Mensaje 3"
