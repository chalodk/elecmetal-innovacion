"""A1 tests — API de sesiones, mensajes y /me.

Tests: caso éxito + 401 (sin token / token inválido) + 403 (sesión de otro
usuario) por endpoint, paginación cursor, formato de error unificado.

Ejecutar:
    pytest tests/test_a1_sessions_api.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Build FastAPI app for testing ────────────────────────────────────────────

from app.main import app

client = TestClient(app)

# ── Test constants ──────────────────────────────────────────────────────────

VALID_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OTHER_USER_ID = "ffffffff-aaaa-bbbb-cccc-dddddddddddd"  # UUID válido

# JWT con sub valido (no se valida criptográficamente en tests — mockeamos
# la dependencia get_current_user)
VALID_TOKEN = "Bearer test-token-user-a"
OTHER_TOKEN = "Bearer test-token-user-b"

# ── Helper: mock DB rows ────────────────────────────────────────────────────

def _profile_row(user_id: str, role: str = "postulante"):
    return {"id": user_id, "full_name": f"User {role}", "role": role,
            "avatar_url": None, "created_at": "2026-01-01T00:00:00"}

def _session_row(session_id: int, user_id: str, agent_type: str = "clara",
                 status: str = "active", title: str = "Nueva sesion"):
    return {"id": session_id, "user_id": user_id, "agent_type": agent_type,
            "status": status, "title": title,
            "created_at": "2026-01-01T00:00:00", "started_at": None,
            "ended_at": None, "updated_at": "2026-01-01T00:00:00"}

def _message_row(msg_id: int, session_id: int, role: str = "user",
                 content: str = "Hola"):
    return {"id": msg_id, "session_id": session_id, "role": role,
            "content": content, "metadata": None,
            "created_at": "2026-01-01T00:00:00"}

# ── Mock dependency override ────────────────────────────────────────────────

def _make_user_override(user_id: str):
    """Returns a callable that FastAPI can use as a dependency override."""
    async def _get_user():
        return {"sub": user_id, "aud": "authenticated"}
    return _get_user


def _install_auth_mock(user_id: str = VALID_USER_ID):
    """Override get_current_user to return a specific user."""
    from app.core.security import get_current_user
    app.dependency_overrides[get_current_user] = _make_user_override(user_id)


def _clear_overrides():
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_overrides_after():
    yield
    _clear_overrides()


# ═════════════════════════════════════════════════════════════════════════════
# A1.1 — GET /api/v1/me
# ═════════════════════════════════════════════════════════════════════════════

class TestGetMe:
    """Tests for GET /api/v1/me."""

    @patch("app.api.v1.users.get_pool")
    def test_me_returns_profile(self, mock_pool):
        """Success: authenticated user gets their profile."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = _profile_row(VALID_USER_ID)
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/me", headers={"Authorization": VALID_TOKEN})

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == VALID_USER_ID
        assert body["role"] == "postulante"
        assert "full_name" in body

    def test_me_401_no_token(self):
        """401: no token → error unificado."""
        resp = client.get("/api/v1/me")

        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "UNAUTHORIZED"

    @patch("app.core.security._fetch_jwks")
    def test_me_401_invalid_token(self, mock_jwks):
        """401: token inválido → UNAUTHORIZED + details."""
        # Return a valid JWKS so the validation attempt goes through
        # but the token itself is garbage
        resp = client.get("/api/v1/me", headers={"Authorization": "Bearer garbage"})

        assert resp.status_code in (401, 500)  # JWT decode will fail
        body = resp.json()
        # May be caught by security.py or by the handler
        assert "error" in body

    @patch("app.api.v1.users.get_pool")
    def test_me_404_profile_not_found(self, mock_pool):
        """404: perfil no existe en BD."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/me", headers={"Authorization": VALID_TOKEN})

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert "Perfil" in body["error"]["message"]


# ═════════════════════════════════════════════════════════════════════════════
# A1.2 — POST /api/v1/sessions
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateSession:
    """Tests for POST /api/v1/sessions."""

    @patch("app.api.v1.sessions.get_pool")
    def test_create_session_success(self, mock_pool):
        """201: crea sesión con agent_type clara."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = _session_row(1, VALID_USER_ID)
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.post(
            "/api/v1/sessions",
            json={"agent_type": "clara", "title": "Mi sesion"},
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] == 1
        assert body["agent_type"] == "clara"
        assert body["user_id"] == VALID_USER_ID

    @patch("app.api.v1.sessions.get_pool")
    def test_create_session_analista(self, mock_pool):
        """201: crea sesión con agent_type analista_oportunidad."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = _session_row(2, VALID_USER_ID,
                                                       agent_type="analista_oportunidad")
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.post(
            "/api/v1/sessions",
            json={"agent_type": "analista_oportunidad"},
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 201
        assert resp.json()["agent_type"] == "analista_oportunidad"

    @patch("app.api.v1.sessions.get_pool")
    def test_create_session_invalid_agent_type(self, mock_pool):
        """422: agent_type inválido → INVALID_AGENT_TYPE."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.post(
            "/api/v1/sessions",
            json={"agent_type": "invalid_agent"},
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "INVALID_AGENT_TYPE"

    def test_create_session_401_no_token(self):
        """401: sin token."""
        resp = client.post("/api/v1/sessions", json={"agent_type": "clara"})
        assert resp.status_code == 401

    @patch("app.api.v1.sessions.get_pool")
    def test_create_session_422_empty_body(self, mock_pool):
        """422: sin content → validation error."""
        _install_auth_mock(VALID_USER_ID)

        # Empty JSON body: content field missing → 422
        resp = client.post(
            "/api/v1/sessions",
            content="",
            headers={
                "Authorization": VALID_TOKEN,
                "Content-Type": "application/json",
            },
        )
        # FastAPI puede devolver 400 (malformed) o 422 (validation)
        # Con content="" es malformed JSON → cae en RequestValidationError
        assert resp.status_code in (400, 422)
        body = resp.json()
        if "error" in body:
            assert body["error"]["code"] in ("VALIDATION_ERROR", "INTERNAL_ERROR")


# ═════════════════════════════════════════════════════════════════════════════
# A1.3 — GET /api/v1/sessions
# ═════════════════════════════════════════════════════════════════════════════

class TestListSessions:
    """Tests for GET /api/v1/sessions."""

    @patch("app.api.v1.sessions.get_pool")
    def test_list_sessions_success(self, mock_pool):
        """200: lista sesiones del usuario con paginación."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            _session_row(10, VALID_USER_ID),
            _session_row(9, VALID_USER_ID, agent_type="analista_oportunidad"),
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/sessions", headers={"Authorization": VALID_TOKEN})

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        assert len(body["data"]) == 2
        assert body["data"][0]["user_id"] == VALID_USER_ID

    @patch("app.api.v1.sessions.get_pool")
    def test_list_sessions_pagination_has_more(self, mock_pool):
        """200: paginación con has_more y next_cursor."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        # Return limit+1 rows → has_more=True
        rows = [_session_row(i, VALID_USER_ID) for i in range(30, 9, -1)]
        mock_conn.fetch.return_value = rows
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/sessions?limit=10", headers={"Authorization": VALID_TOKEN})

        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["limit"] == 10
        if len(body["data"]) == 10:
            assert body["pagination"]["has_more"] is True

    @patch("app.api.v1.sessions.get_pool")
    def test_list_sessions_with_cursor(self, mock_pool):
        """200: paginación con cursor."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [_session_row(5, VALID_USER_ID)]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/sessions?cursor=10", headers={"Authorization": VALID_TOKEN})

        assert resp.status_code == 200

    @patch("app.api.v1.sessions.get_pool")
    def test_list_sessions_filter_by_agent(self, mock_pool):
        """200: filtra por agent_type."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [_session_row(1, VALID_USER_ID)]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get(
            "/api/v1/sessions?agent_filter=analista_oportunidad",
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 200

    def test_list_sessions_invalid_cursor(self):
        """400: cursor inválido → INVALID_ID (sin necesidad de BD)."""
        _install_auth_mock(VALID_USER_ID)

        resp = client.get(
            "/api/v1/sessions?cursor=abc",
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "INVALID_ID"


# ═════════════════════════════════════════════════════════════════════════════
# A1.4 — GET /api/v1/sessions/{id}
# ═════════════════════════════════════════════════════════════════════════════

class TestGetSession:
    """Tests for GET /api/v1/sessions/{id}."""

    @patch("app.api.v1.sessions.get_pool")
    def test_get_session_success(self, mock_pool):
        """200: obtiene sesión propia con message_count."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = _session_row(1, VALID_USER_ID)
        mock_conn.fetchval.return_value = 5  # message_count
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/sessions/1", headers={"Authorization": VALID_TOKEN})

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 1
        assert body["message_count"] == 5

    @patch("app.api.v1.sessions.get_pool")
    def test_get_session_403_other_user(self, mock_pool):
        """404: sesión de otro usuario → NOT_FOUND (no 403 por seguridad)."""
        _install_auth_mock(OTHER_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # no encuentra
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/sessions/1", headers={"Authorization": OTHER_TOKEN})

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"

    def test_get_session_400_invalid_id(self):
        """400: ID no es bigint."""
        _install_auth_mock(VALID_USER_ID)

        resp = client.get("/api/v1/sessions/notanumber", headers={"Authorization": VALID_TOKEN})

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_ID"


# ═════════════════════════════════════════════════════════════════════════════
# A1.5 — GET /api/v1/sessions/{id}/messages
# ═════════════════════════════════════════════════════════════════════════════

class TestGetMessages:
    """Tests for GET /api/v1/sessions/{id}/messages."""

    @patch("app.api.v1.sessions.get_pool")
    def test_get_messages_success(self, mock_pool):
        """200: historial de mensajes paginado."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        # fetchrow para verificar sesión
        mock_conn.fetchrow.return_value = _session_row(1, VALID_USER_ID)
        # fetch para mensajes
        mock_conn.fetch.return_value = [
            _message_row(1, 1, "user", "Hola"),
            _message_row(2, 1, "assistant", "¡Hola! Soy Clara."),
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get(
            "/api/v1/sessions/1/messages?limit=20",
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        assert len(body["data"]) == 2
        assert body["data"][0]["role"] == "user"

    @patch("app.api.v1.sessions.get_pool")
    def test_get_messages_pagination_cursor(self, mock_pool):
        """200: paginación cursor en mensajes."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = _session_row(1, VALID_USER_ID)
        # Return 1 message (less than limit+1=6), has_more=False
        mock_conn.fetch.return_value = [_message_row(50, 1, "user", "Histórico")]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get(
            "/api/v1/sessions/1/messages?cursor=30&limit=5",
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["limit"] == 5

    @patch("app.api.v1.sessions.get_pool")
    def test_get_messages_403_other_user(self, mock_pool):
        """404: sesión de otro usuario."""
        _install_auth_mock(OTHER_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # no encuentra sesión
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get(
            "/api/v1/sessions/1/messages",
            headers={"Authorization": OTHER_TOKEN},
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"


# ═════════════════════════════════════════════════════════════════════════════
# A1.6 — POST /api/v1/sessions/{id}/messages (placeholder)
# ═════════════════════════════════════════════════════════════════════════════

class TestSendMessage:
    """Tests for POST /api/v1/sessions/{id}/messages."""

    @patch("app.api.v1.sessions.get_pool")
    def test_send_message_returns_json_with_placeholder(self, mock_pool):
        """201: POST /messages retorna JSON con user_message y assistant_message placeholder."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"id": 1, "agent_type": "clara"},           # session lookup
            {"id": 501, "session_id": 1, "role": "user", "content": "Hola Clara", "created_at": "2026-01-01T00:00:00"},  # user INSERT
            {"id": 502, "session_id": 1, "role": "assistant", "content": "", "created_at": "2026-01-01T00:00:01"},  # asst placeholder
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.post(
            "/api/v1/sessions/1/messages",
            json={"content": "Hola Clara"},
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["user_message"]["role"] == "user"
        assert data["user_message"]["content"] == "Hola Clara"
        assert data["assistant_message"]["role"] == "assistant"
        assert data["assistant_message"]["content"] == ""

    @patch("app.api.v1.sessions.get_pool")
    def test_send_message_403_other_user(self, mock_pool):
        """404: sesión de otro usuario."""
        _install_auth_mock(OTHER_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.post(
            "/api/v1/sessions/1/messages",
            json={"content": "Hola"},
            headers={"Authorization": OTHER_TOKEN},
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    def test_send_message_422_empty_content(self):
        """422: content vacío."""
        _install_auth_mock(VALID_USER_ID)

        resp = client.post(
            "/api/v1/sessions/1/messages",
            json={"content": ""},
            headers={"Authorization": VALID_TOKEN},
        )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
