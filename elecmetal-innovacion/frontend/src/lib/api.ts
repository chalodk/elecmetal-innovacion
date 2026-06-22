const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function authFetch(token: string, path: string, options?: RequestInit) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // Unified error format: {"error": {"code": "...", "message": "...", "details": {...}}}
    const message = body.error?.message || body.detail || `Error ${res.status}`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchMe(token: string) {
  return authFetch(token, "/api/v1/me");
}

export async function healthCheck() {
  const res = await fetch(`${API_URL}/api/v1/health`);
  return res.json();
}

// ── Initiatives ─────────────────────────────────────────────────────────────

export async function listInitiatives(token: string) {
  return authFetch(token, "/api/v1/initiatives");
}

export async function getInitiative(token: string, initiativeId: string) {
  return authFetch(token, `/api/v1/initiatives/${initiativeId}`);
}

export async function updateInitiativeStatus(
  token: string,
  initiativeId: string,
  status: string,
) {
  return authFetch(token, `/api/v1/initiatives/${initiativeId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function triggerEvaluation(
  token: string,
  initiativeId: string,
) {
  return authFetch(token, `/api/v1/initiatives/${initiativeId}/evaluation`, {
    method: "POST",
  });
}

// ── Evaluations ─────────────────────────────────────────────────────────────

export async function getEvaluation(token: string, evaluationId: string) {
  return authFetch(token, `/api/v1/evaluations/${evaluationId}`);
}

export async function getEvaluationByInitiative(
  token: string,
  initiativeId: string,
) {
  return authFetch(token, `/api/v1/initiatives/${initiativeId}/evaluation`);
}

export async function reviewEvaluation(
  token: string,
  evaluationId: string,
  body: { results?: unknown; veredicto?: string; validate?: boolean },
) {
  return authFetch(token, `/api/v1/evaluations/${evaluationId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ── Notifications ───────────────────────────────────────────────────────────

export async function listNotifications(token: string) {
  return authFetch(token, "/api/v1/notifications");
}

export async function processNotifications(token: string) {
  return authFetch(token, "/api/v1/notifications/process", {
    method: "POST",
  });
}

// ── Sessions ──────────────────────────────────────────────────────────────

export async function createSession(
  token: string,
  agentType: string = "clara",
) {
  return authFetch(token, "/api/v1/sessions", {
    method: "POST",
    body: JSON.stringify({ agent_type: agentType }),
  });
}

export async function listSessions(token: string) {
  return authFetch(token, "/api/v1/sessions");
}

// ── Messages ──────────────────────────────────────────────────────────────

export interface PaginatedMessages {
  data: Array<{
    id: number;
    session_id: number;
    role: "user" | "assistant" | "system";
    content: string;
    metadata: unknown;
    created_at: string;
  }>;
  pagination: {
    has_more: boolean;
    next_cursor: string | null;
    limit: number;
  };
}

export async function getMessages(
  token: string,
  sessionId: string,
  cursor?: string | null,
): Promise<PaginatedMessages> {
  const params = new URLSearchParams();
  if (cursor) params.set("cursor", cursor);
  return authFetch(
    token,
    `/api/v1/sessions/${sessionId}/messages?${params.toString()}`,
  );
}

export interface SSEEvent {
  token?: string;
  done?: boolean;
  message_id?: number;
  error?: string;
  initiative?: {
    initiative_id: number;
    initiative_code: string;
    status: string;
  } | {
    parse_error?: string;
    persistence_error?: string;
  };
}

export async function sendMessage(
  token: string,
  sessionId: string,
  content: string,
  onToken?: (token: string) => void,
): Promise<{ content: string; message_id: number; initiative?: SSEEvent["initiative"] }> {
  const res = await fetch(`${API_URL}/api/v1/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = body.error?.message || body.detail || `Error ${res.status}`;
    throw new Error(message);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let fullContent = "";
  let messageId = 0;
  let initiative: SSEEvent["initiative"] | undefined;
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    // Keep the last partial line in the buffer
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload: SSEEvent = JSON.parse(line.slice(6));

      if (payload.error) {
        throw new Error(payload.error);
      }

      if (payload.token) {
        fullContent += payload.token;
        onToken?.(payload.token);
      }

      if (payload.done) {
        messageId = payload.message_id ?? 0;
        initiative = payload.initiative;
      }
    }
  }

  return { content: fullContent, message_id: messageId, initiative };
}

// ── Diego-compatible aliases (B1/B2/B3 hooks) ───────────────────────────────

/** Alias for listSessions returning paginated envelope format. */
export async function fetchSessions(token: string) {
  const data = await listSessions(token);
  return { data: Array.isArray(data) ? data : (data.data || []) };
}

/** Get a single session by ID. */
export async function fetchSession(token: string, id: number) {
  return authFetch(token, `/api/v1/sessions/${id}`);
}

/** Paginated messages — Diego-compatible signature. */
export async function fetchMessages(
  token: string,
  sessionId: number,
  opts?: { limit?: number; cursor?: number },
) {
  const params = new URLSearchParams();
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.cursor) params.set("cursor", String(opts.cursor));
  return authFetch(token, `/api/v1/sessions/${sessionId}/messages?${params.toString()}`);
}

/** Filtered initiative list — Diego-compatible signature. */
export async function fetchInitiatives(
  token: string,
  params?: { status?: string; cursor?: number; limit?: number },
) {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.cursor) sp.set("cursor", String(params.cursor));
  if (params?.limit) sp.set("limit", String(params.limit));
  return authFetch(token, `/api/v1/initiatives?${sp.toString()}`);
}

/** Single initiative — Diego-compatible alias for getInitiative. */
export async function fetchInitiative(token: string, id: number) {
  return authFetch(token, `/api/v1/initiatives/${id}`);
}

/** Plain POST to send a message (no SSE). Returns {user_message, assistant_message?}. */
export async function postMessage(
  token: string,
  sessionId: number,
  content: string,
) {
  return authFetch(token, `/api/v1/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}
