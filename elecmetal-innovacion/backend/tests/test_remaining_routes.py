"""Tests HTTP para notifications, initiatives y evaluations.

Cubre exito + 401 (sin token) + 403 (rol insuficiente) por endpoint,
siguiendo el mismo patron que test_a1_sessions_api.py.

Ejecutar:
    pytest tests/test_remaining_routes.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ── Test constants ──────────────────────────────────────────────────────────

VALID_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
DIRECTORA_ID = "dddddddd-aaaa-bbbb-cccc-dddddddddddd"
VALID_TOKEN = "Bearer test-token-user-a"
DIRECTORA_TOKEN = "Bearer test-token-directora"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_user_override(user_id: str):
    async def _get_user():
        return {"sub": user_id, "aud": "authenticated"}
    return _get_user


def _install_auth_mock(user_id: str = VALID_USER_ID):
    from app.core.security import get_current_user
    app.dependency_overrides[get_current_user] = _make_user_override(user_id)


def _clear_overrides():
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_overrides_after():
    yield
    _clear_overrides()


# ═════════════════════════════════════════════════════════════════════════════
# Notifications
# ═════════════════════════════════════════════════════════════════════════════

class TestListNotifications:
    """GET /api/v1/notifications"""

    @patch("app.api.v1.notifications.get_pool")
    def test_list_notifications_success(self, mock_pool):
        """200: listado paginado de notificaciones del usuario."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"id": 1, "initiative_id": 10, "notification_type": "receipt_to_applicant",
             "status": "pending", "sent_at": None, "created_at": "2026-01-01T00:00:00",
             "initiative_code": "INI-2026-001", "initiative_title": "Test"},
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/notifications", headers={"Authorization": VALID_TOKEN})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        assert body["pagination"]["limit"] == 20

    def test_list_notifications_401_no_token(self):
        """401: sin token."""
        resp = client.get("/api/v1/notifications")
        assert resp.status_code == 401


class TestProcessNotifications:
    """POST /api/v1/notifications/process"""

    @patch("app.api.v1.notifications.require_directora")
    @patch("app.api.v1.notifications.process_pending")
    def test_process_success_as_directora(self, mock_process, mock_require):
        """200: directora dispara procesamiento."""
        _install_auth_mock(DIRECTORA_ID)
        mock_require.return_value = DIRECTORA_ID
        mock_process.return_value = {"found": 2, "sent": 2, "failed": 0, "skipped": 0}

        resp = client.post(
            "/api/v1/notifications/process",
            headers={"Authorization": DIRECTORA_TOKEN},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["found"] == 2
        assert body["sent"] == 2

    @patch("app.api.v1.notifications.require_directora")
    def test_process_403_not_directora(self, mock_require):
        """403: postulante sin permisos."""
        _install_auth_mock(VALID_USER_ID)

        from app.core.errors import AppError, ErrorCode
        mock_require.side_effect = AppError(code=ErrorCode.FORBIDDEN, message="Solo directora")

        resp = client.post(
            "/api/v1/notifications/process",
            headers={"Authorization": VALID_TOKEN},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "FORBIDDEN"

    def test_process_401_no_token(self):
        """401: sin token."""
        resp = client.post("/api/v1/notifications/process")
        assert resp.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# Initiatives
# ═════════════════════════════════════════════════════════════════════════════

class TestListInitiatives:
    """GET /api/v1/initiatives"""

    @patch("app.api.v1.initiatives.get_pool")
    def test_list_initiatives_success(self, mock_pool):
        """200: listado paginado (postulante solo ve las suyas)."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"role": "postulante"}
        mock_conn.fetch.return_value = [
            {"id": 1, "session_id": 5, "user_id": VALID_USER_ID,
             "status": "persistido", "initiative_code": "INI-2026-001",
             "title": "Test", "initiative_type": "interna",
             "postulation_date": "2026-01-01", "area": "Fundicion",
             "applicant_name": "User", "trl": 4, "crl": 3, "brl": 2,
             "scalability": "Interna", "return_horizon": 12,
             "strategic_alignment": None, "created_at": "2026-01-01T00:00:00",
             "updated_at": "2026-01-01T00:00:00"},
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/initiatives", headers={"Authorization": VALID_TOKEN})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert body["pagination"]["limit"] == 20

    def test_list_initiatives_401_no_token(self):
        """401: sin token."""
        resp = client.get("/api/v1/initiatives")
        assert resp.status_code == 401


class TestGetInitiative:
    """GET /api/v1/initiatives/{id}"""

    @patch("app.api.v1.initiatives.get_pool")
    def test_get_initiative_success(self, mock_pool):
        """200: obtener iniciativa por ID (dueño)."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"role": "postulante"},  # role check
            {"id": 1, "status": "persistido", "initiative_code": "INI-2026-001",
             "title": "Test", "session_id": 5, "user_id": VALID_USER_ID,
             "initiative_type": "interna", "postulation_date": "2026-01-01",
             "area": "Fundicion", "applicant_name": "User",
             "trl": 4, "crl": 3, "brl": 2, "scalability": "Interna",
             "return_horizon": 12, "strategic_alignment": None,
             "dbi_extra": None, "dbi_raw_text": "test",
             "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
             "problem": "", "solution": "", "economic_impact": "",
             "internal_client": "", "external_client": "",
             "sponsor": "", "internal_team": "", "external_team": "",
             "estimated_duration": "", "main_doubt": "", "key_condition": "",
             "value_capture": "", "technical_milestones": "", "financial_milestones": ""},
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/initiatives/1", headers={"Authorization": VALID_TOKEN})
        assert resp.status_code == 200
        body = resp.json()
        assert body["initiative_code"] == "INI-2026-001"

    @patch("app.api.v1.initiatives.get_pool")
    def test_get_initiative_404_other_user(self, mock_pool):
        """404: iniciativa de otro usuario (postulante)."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"role": "postulante"},  # role check
            None,  # no initiative found for this user
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get("/api/v1/initiatives/1", headers={"Authorization": VALID_TOKEN})
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    def test_get_initiative_401_no_token(self):
        """401: sin token."""
        resp = client.get("/api/v1/initiatives/1")
        assert resp.status_code == 401

    def test_get_initiative_400_invalid_id(self):
        """400: initiative_id invalido."""
        _install_auth_mock(VALID_USER_ID)
        resp = client.get("/api/v1/initiatives/notanumber", headers={"Authorization": VALID_TOKEN})
        assert resp.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# Evaluations — PATCH /initiatives/{id}/status
# ═════════════════════════════════════════════════════════════════════════════

class TestUpdateInitiativeStatus:
    """PATCH /api/v1/initiatives/{id}/status"""

    @patch("app.api.v1.evaluations.get_pool")
    @patch("app.api.v1.evaluations.require_directora")
    def test_update_status_success(self, mock_require, mock_pool):
        """200: directora mueve iniciativa a en_evaluacion."""
        _install_auth_mock(DIRECTORA_ID)
        mock_require.return_value = DIRECTORA_ID

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"id": 1, "status": "notificado"},                 # lookup
            {"id": 1, "status": "en_evaluacion", "updated_at": "2026-01-02T00:00:00"},  # read back
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.patch(
            "/api/v1/initiatives/1/status",
            json={"status": "en_evaluacion"},
            headers={"Authorization": DIRECTORA_TOKEN},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "en_evaluacion"

    @patch("app.api.v1.evaluations.require_directora")
    def test_update_status_403_not_directora(self, mock_require):
        """403: postulante no puede cambiar estado."""
        _install_auth_mock(VALID_USER_ID)

        from app.core.errors import AppError, ErrorCode
        mock_require.side_effect = AppError(code=ErrorCode.FORBIDDEN, message="Solo directora")

        resp = client.patch(
            "/api/v1/initiatives/1/status",
            json={"status": "en_evaluacion"},
            headers={"Authorization": VALID_TOKEN},
        )
        assert resp.status_code == 403

    def test_update_status_401_no_token(self):
        """401: sin token."""
        resp = client.patch("/api/v1/initiatives/1/status", json={"status": "en_evaluacion"})
        assert resp.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# Evaluations — POST /initiatives/{id}/evaluation
# ═════════════════════════════════════════════════════════════════════════════

class TestTriggerEvaluation:
    """POST /api/v1/initiatives/{id}/evaluation"""

    @patch("app.api.v1.evaluations.require_directora")
    @patch("app.api.v1.evaluations.create_evaluation")
    def test_trigger_success(self, mock_create, mock_require):
        """201: directora activa evaluador IA."""
        _install_auth_mock(DIRECTORA_ID)
        mock_require.return_value = DIRECTORA_ID
        mock_create.return_value = {
            "id": 1, "initiative_id": 1, "activated_by": DIRECTORA_ID,
            "status": "in_progress", "results": None, "reviewed_by": None,
            "reviewed_at": None, "veredicto": None,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
        }

        resp = client.post(
            "/api/v1/initiatives/1/evaluation",
            headers={"Authorization": DIRECTORA_TOKEN},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] in ("in_progress", "pending")

    @patch("app.api.v1.evaluations.require_directora")
    def test_trigger_403_not_directora(self, mock_require):
        """403: postulante no puede activar evaluador."""
        _install_auth_mock(VALID_USER_ID)

        from app.core.errors import AppError, ErrorCode
        mock_require.side_effect = AppError(code=ErrorCode.FORBIDDEN, message="Solo directora")

        resp = client.post(
            "/api/v1/initiatives/1/evaluation",
            headers={"Authorization": VALID_TOKEN},
        )
        assert resp.status_code == 403

    def test_trigger_401_no_token(self):
        """401: sin token."""
        resp = client.post("/api/v1/initiatives/1/evaluation")
        assert resp.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# Evaluations — GET lookups
# ═════════════════════════════════════════════════════════════════════════════

class TestGetEvaluations:
    """GET /api/v1/initiatives/{id}/evaluation + GET /api/v1/evaluations/{id}"""

    @patch("app.api.v1.evaluations.get_pool")
    def test_get_by_initiative_success(self, mock_pool):
        """200: obtener evaluacion via initiative_id."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "id": 1, "initiative_id": 1, "activated_by": DIRECTORA_ID,
            "status": "completed", "results": '{"score": 85}',
            "reviewed_by": None, "reviewed_at": None, "veredicto": "pendiente",
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
        }
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get(
            "/api/v1/initiatives/1/evaluation",
            headers={"Authorization": VALID_TOKEN},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["results"]["score"] == 85

    @patch("app.api.v1.evaluations.get_pool")
    def test_get_by_id_success(self, mock_pool):
        """200: obtener evaluacion por su ID."""
        _install_auth_mock(VALID_USER_ID)

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "id": 1, "initiative_id": 1, "activated_by": DIRECTORA_ID,
            "status": "pending", "results": None,
            "reviewed_by": None, "reviewed_at": None, "veredicto": None,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
        }
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.get(
            "/api/v1/evaluations/1",
            headers={"Authorization": VALID_TOKEN},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 1

    def test_get_by_initiative_401_no_token(self):
        resp = client.get("/api/v1/initiatives/1/evaluation")
        assert resp.status_code == 401

    def test_get_by_id_401_no_token(self):
        resp = client.get("/api/v1/evaluations/1")
        assert resp.status_code == 401

    def test_get_by_initiative_400_invalid_id(self):
        _install_auth_mock(VALID_USER_ID)
        resp = client.get("/api/v1/initiatives/notanumber/evaluation", headers={"Authorization": VALID_TOKEN})
        assert resp.status_code == 400

    def test_get_by_id_400_invalid_id(self):
        _install_auth_mock(VALID_USER_ID)
        resp = client.get("/api/v1/evaluations/notanumber", headers={"Authorization": VALID_TOKEN})
        assert resp.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# Evaluations — PATCH /evaluations/{id}
# ═════════════════════════════════════════════════════════════════════════════

class TestReviewEvaluation:
    """PATCH /api/v1/evaluations/{id}"""

    @patch("app.api.v1.evaluations.get_pool")
    @patch("app.api.v1.evaluations.require_directora")
    def test_review_success(self, mock_require, mock_pool):
        """200: directora revisa y valida evaluacion."""
        _install_auth_mock(DIRECTORA_ID)
        mock_require.return_value = DIRECTORA_ID

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"id": 1, "initiative_id": 1, "status": "completed",
             "activated_by": DIRECTORA_ID, "results": None,
             "reviewed_by": None, "reviewed_at": None, "veredicto": None,
             "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00"},
            {"id": 1, "initiative_id": 1, "status": "completed",
             "activated_by": DIRECTORA_ID, "results": '{"score": 85}',
             "reviewed_by": DIRECTORA_ID, "reviewed_at": "2026-01-02T00:00:00",
             "veredicto": "aprobada",
             "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-02T00:00:00"},
        ]
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        resp = client.patch(
            "/api/v1/evaluations/1",
            json={"veredicto": "aprobada", "validate": True},
            headers={"Authorization": DIRECTORA_TOKEN},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["veredicto"] == "aprobada"

    @patch("app.api.v1.evaluations.require_directora")
    def test_review_403_not_directora(self, mock_require):
        """403: postulante no puede revisar evaluaciones."""
        _install_auth_mock(VALID_USER_ID)

        from app.core.errors import AppError, ErrorCode
        mock_require.side_effect = AppError(code=ErrorCode.FORBIDDEN, message="Solo directora")

        resp = client.patch(
            "/api/v1/evaluations/1",
            json={"veredicto": "aprobada"},
            headers={"Authorization": VALID_TOKEN},
        )
        assert resp.status_code == 403

    def test_review_401_no_token(self):
        resp = client.patch("/api/v1/evaluations/1", json={"veredicto": "aprobada"})
        assert resp.status_code == 401
