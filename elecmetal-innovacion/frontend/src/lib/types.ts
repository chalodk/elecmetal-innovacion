// ─── API Response Types ──────────────────────────────────────

export interface UserProfile {
  id: string;
  full_name: string;
  role: "postulante" | "directora" | "admin";
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export type AgentType = "clara" | "analista_oportunidad";

export type SessionStatus = "active" | "completed" | "abandoned";

export interface Session {
  id: number;
  user_id: string;
  agent_type: AgentType;
  status: SessionStatus;
  title: string | null;
  started_at: string;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionsResponse {
  data: Session[];
}

// ─── Message Types ────────────────────────────────────────────

export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  id: number;
  session_id: number;
  role: MessageRole;
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface MessagesResponse {
  data: Message[];
  pagination: {
    next_cursor: number | null;
    has_more: boolean;
  };
}

export interface SendMessageResponse {
  user_message: Message;
  /** Solo presente en modo placeholder (sin OpenAI). Con OpenAI real, la
   * respuesta del asistente llega via SSE stream y se persiste al final. */
  assistant_message?: Message;
}

// ─── Initiative Types ─────────────────────────────────────────

export type InitiativeStatus =
  | "dbi_generado"
  | "persistido"
  | "notificado"
  | "en_evaluacion"
  | "evaluado"
  | "validado"
  | "veredicto";

export interface Initiative {
  id: number;
  session_id: number | null;
  user_id: string;
  status: InitiativeStatus;
  initiative_code: string;
  title: string;
  initiative_type: string;
  postulation_date: string | null;
  area: string;
  applicant_name: string;
  problem?: string;
  solution?: string;
  economic_impact?: string | null;
  trl?: number | null;
  scalability?: string | null;
  internal_client?: string | null;
  external_client?: string | null;
  crl?: number | null;
  sponsor?: string | null;
  internal_team?: string | null;
  external_team?: string | null;
  estimated_duration?: string | null;
  main_doubt?: string | null;
  key_condition?: string | null;
  value_capture?: string | null;
  brl?: number | null;
  technical_milestones?: string | null;
  financial_milestones?: string | null;
  return_horizon?: number | null;
  strategic_alignment?: string | null;
  dbi_raw_text?: string | null;
  dbi_extra?: Record<string, unknown> | null;
  evaluation?: EvaluationSummary;
  created_at: string;
  updated_at: string;
}

export interface InitiativeListResponse {
  data: Initiative[];
  pagination: {
    next_cursor: number | null;
    has_more: boolean;
  };
}

export interface EvaluationSummary {
  id: number;
  status: string;
  results: Record<string, unknown> | null;
  veredicto: string | null;
  reviewed_at: string | null;
}

// ─── Error Types ──────────────────────────────────────────────

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
