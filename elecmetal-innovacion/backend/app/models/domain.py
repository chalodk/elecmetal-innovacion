"""Pydantic models for the Elecmetal Innovacion API.

These models define the request/response schemas used across endpoints.
They serve as the single source of truth for API contracts.

Convention: fields use Python snake_case, which FastAPI serializes to
camelCase via its built-in alias generator (or explicit alias where needed).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class AgentType(str, Enum):
    CLARA = "clara"
    ANALISTA_OPORTUNIDAD = "analista_oportunidad"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class InitiativeStatus(str, Enum):
    DBI_GENERADO = "dbi_generado"
    PERSISTIDO = "persistido"
    NOTIFICADO = "notificado"
    EN_EVALUACION = "en_evaluacion"
    EVALUADO = "evaluado"
    VALIDADO = "validado"
    VEREDICTO = "veredicto"


class InitiativeType(str, Enum):
    INTERNA = "interna"
    EXTERNA = "externa"
    MIXTA = "mixta"


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class NotificationType(str, Enum):
    RECEIPT_TO_APPLICANT = "receipt_to_applicant"
    NOTICE_TO_DIRECTOR = "notice_to_director"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Veredicto(str, Enum):
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    PENDIENTE = "pendiente"


class UserRole(str, Enum):
    POSTULANTE = "postulante"
    DIRECTORA = "directora"
    ADMIN = "admin"


class Scalability(str, Enum):
    LOCAL = "Local"
    INTERNA = "Interna"
    EXTERNA = "Externa"


# ── Pagination ───────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    """Metadata for cursor-based paginated responses."""
    has_more: bool
    next_cursor: str | None
    limit: int


class PaginatedResponse(BaseModel):
    """Generic paginated response envelope."""
    data: list[Any]
    pagination: PaginationMeta


# ── Profile ──────────────────────────────────────────────────────────────────

class ProfileResponse(BaseModel):
    """Response for GET /api/v1/me."""
    id: str
    full_name: str
    role: str
    avatar_url: str | None = None
    created_at: str | None = None


# ── Sessions ─────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    """Request for POST /api/v1/sessions."""
    agent_type: str = Field(default="clara", examples=["clara", "analista_oportunidad"])
    title: str = Field(default="Nueva sesion", max_length=255)


class SessionResponse(BaseModel):
    """Response for a session object."""
    id: int
    agent_type: str | None = None
    status: str | None = None
    title: str | None = None
    created_at: str | None = None
    user_id: str | None = None


class SessionDetailResponse(SessionResponse):
    """Response for GET /api/v1/sessions/{id} — includes extra metadata."""
    started_at: str | None = None
    ended_at: str | None = None
    updated_at: str | None = None
    message_count: int = 0


class SendMessageRequest(BaseModel):
    """Request for POST /api/v1/sessions/{id}/messages."""
    content: str = Field(..., min_length=1)


class UpdateSessionRequest(BaseModel):
    """Request for PATCH /api/v1/sessions/{id}."""
    title: str = Field(..., min_length=1, max_length=255)


# ── Messages ─────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Response for a message object."""
    id: int
    session_id: int
    role: str
    content: str
    metadata: dict | None = None
    created_at: str | None = None


# ── Initiatives ──────────────────────────────────────────────────────────────

class InitiativeSummary(BaseModel):
    """Summary view of an initiative (list endpoints)."""
    id: int
    session_id: int | None = None
    user_id: str | None = None
    status: str
    initiative_code: str
    title: str
    initiative_type: str
    postulation_date: str | None = None
    area: str | None = None
    applicant_name: str | None = None
    trl: int | None = None
    crl: int | None = None
    brl: int | None = None
    scalability: str | None = None
    return_horizon: int | None = None
    strategic_alignment: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class InitiativeDetail(InitiativeSummary):
    """Full view of an initiative (GET /{id})."""
    problem: str | None = None
    solution: str | None = None
    economic_impact: str | None = None
    internal_client: str | None = None
    external_client: str | None = None
    sponsor: str | None = None
    internal_team: str | None = None
    external_team: str | None = None
    estimated_duration: str | None = None
    main_doubt: str | None = None
    key_condition: str | None = None
    value_capture: str | None = None
    technical_milestones: str | None = None
    financial_milestones: str | None = None
    dbi_raw_text: str | None = None
    dbi_extra: dict | None = None


class UpdateInitiativeStatusRequest(BaseModel):
    """Request for PATCH /api/v1/initiatives/{id}/status."""
    status: str = Field(..., pattern=r"^(en_evaluacion)$")


# ── Evaluations ──────────────────────────────────────────────────────────────

class EvaluationResponse(BaseModel):
    """Response for an evaluation object."""
    id: int
    initiative_id: int
    activated_by: str
    status: str
    results: dict | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    veredicto: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ReviewEvaluationRequest(BaseModel):
    """Request for PATCH /api/v1/evaluations/{id}."""
    results: dict | None = None
    veredicto: str | None = Field(None, pattern=r"^(aprobada|rechazada|pendiente)$")
    validate: bool = False


# ── Notifications ────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    """Response for a notification object."""
    id: int
    initiative_id: int
    notification_type: str
    status: str
    sent_at: str | None = None
    created_at: str | None = None
    initiative_code: str | None = None
    initiative_title: str | None = None


class ProcessNotificationsResponse(BaseModel):
    """Response for POST /api/v1/notifications/process."""
    found: int = 0
    sent: int = 0
    failed: int = 0
    skipped: int = 0


# ── SSE Events ───────────────────────────────────────────────────────────────

class SSEEvent(BaseModel):
    """Server-Sent Event payload for streaming responses."""
    token: str | None = None
    done: bool | None = None
    message_id: int | None = None
    error: str | None = None
    initiative: dict | None = None
