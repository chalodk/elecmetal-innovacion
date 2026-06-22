import { http, HttpResponse, delay } from "msw";

const API_URL = "http://localhost:8000";

// ─── Mock SSE helpers ──────────────────────────────────────────

const MOCK_CLARA_REPLY =
  "¡Hola! Soy Clara, tu asistente de innovación. " +
  "He analizado tu consulta y encuentro varias oportunidades interesantes. " +
  "Podemos explorar mejoras en eficiencia operativa, reducción de costos " +
  "y nuevas tecnologías aplicables a tu proceso. " +
  "¿Te gustaría que profundice en algún aspecto en particular?";

/**
 * Divide el texto en tokens simulados (palabras + espacios)
 * para el efecto typewriter.
 */
function tokenize(text: string): string[] {
  // Dividir por palabra manteniendo espacios como tokens independientes
  return text.split(/(\s+)/).filter(Boolean);
}

function createSSEResponse(
  tokens: string[],
  simulateErrorAfter?: number,
): HttpResponse {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      for (let i = 0; i < tokens.length; i++) {
        // Simular latencia de red (30-80ms por token)
        await delay(Math.floor(Math.random() * 50) + 30);

        // Simular error a mitad del stream si se solicita
        if (simulateErrorAfter !== undefined && i === simulateErrorAfter) {
          controller.error(new Error("Stream broken"));
          return;
        }

        const chunk = `data: ${JSON.stringify({ token: tokens[i] })}\n\n`;
        controller.enqueue(encoder.encode(chunk));
      }
      controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      controller.close();
    },
  });

  return new HttpResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}

export const mockProfile = {
  id: "test-user-id",
  full_name: "Camila Gómez",
  role: "postulante" as const,
  avatar_url: null,
  created_at: "2026-06-17T10:00:00-04:00",
  updated_at: "2026-06-17T10:00:00-04:00",
};

export const mockDirectoraProfile = {
  id: "directora-user-id",
  full_name: "María Valdés",
  role: "directora" as const,
  avatar_url: null,
  created_at: "2026-06-01T10:00:00-04:00",
  updated_at: "2026-06-01T10:00:00-04:00",
};

export const mockMessages = [
  {
    id: 1,
    session_id: 1,
    role: "user" as const,
    content: "Hola Clara, necesito ayuda con mi postulación",
    metadata: null,
    created_at: "2026-06-17T15:30:00-04:00",
  },
  {
    id: 2,
    session_id: 1,
    role: "assistant" as const,
    content: "¡Hola! Claro que sí, cuéntame más sobre tu iniciativa.",
    metadata: null,
    created_at: "2026-06-17T15:30:30-04:00",
  },
];

let messageIdCounter = 10;

// ─── Mock Initiatives ─────────────────────────────────────────

export const mockInitiatives = [
  {
    id: 101,
    session_id: 1,
    user_id: "test-user-id",
    status: "notificado" as const,
    initiative_code: "INI-2026-001",
    title: "Optimización de ciclo de molienda SAG",
    initiative_type: "interna" as const,
    postulation_date: "2026-06-15",
    area: "Mantención Planta",
    applicant_name: "Carlos Muñoz",
    problem:
      "El ciclo de molienda SAG presenta pérdidas de eficiencia del 15% por desgaste prematuro de revestimientos.",
    solution:
      "Implementar un sistema de monitoreo continuo con sensores IoT para predecir fallas y optimizar cambios de revestimientos.",
    economic_impact: "Ahorro estimado de USD 200K/año en repuestos y reducción de detenciones no programadas.",
    trl: 5,
    scalability: "Interna",
    internal_client: "Superintendencia de Molienda",
    external_client: null,
    crl: 4,
    sponsor: "Juan Pereira — Gerente de Operaciones",
    internal_team: "Equipo de mantenciones (4 personas)",
    external_team: null,
    estimated_duration: "8 meses",
    main_doubt: "Disponibilidad de sensores certificados para ambientes de alta vibración.",
    key_condition: "Aprobar presupuesto de USD 45K para fase piloto.",
    value_capture: "ahorro",
    brl: 4,
    technical_milestones: "Mes 1-2: piloto 3 molinos; Mes 3-4: validación datos; Mes 5-8: despliegue.",
    financial_milestones: "ROI esperado a 18 meses.",
    return_horizon: 18,
    strategic_alignment: "H2 — Eficiencia Operacional",
    dbi_raw_text: null,
    dbi_extra: null,
    created_at: "2026-06-15T14:30:00-04:00",
    updated_at: "2026-06-15T14:30:00-04:00",
  },
  {
    id: 102,
    session_id: 2,
    user_id: "test-user-id",
    status: "en_evaluacion" as const,
    initiative_code: "INI-2026-002",
    title: "Recuperación de bolas de acero desde escoria",
    initiative_type: "externa" as const,
    postulation_date: "2026-06-12",
    area: "Fundición",
    applicant_name: "Ana López",
    problem:
      "Se pierden aproximadamente 50 ton/mes de bolas de acero en la escoria del horno de refino.",
    solution:
      "Sistema magnético de recuperación en línea de salida de escoria, con clasificación automática.",
    economic_impact: "Recuperación de USD 180K/año en material reutilizable.",
    trl: 7,
    scalability: "Local",
    internal_client: "Operaciones Fundición",
    external_client: null,
    crl: 5,
    sponsor: "Roberto Díaz — Jefe de Fundición",
    internal_team: "Ingeniería de procesos (3 personas)",
    external_team: "Proveedor de imanes industriales (cotización en curso)",
    estimated_duration: "6 meses",
    main_doubt: "Compatibilidad del sistema magnético con temperaturas de 800°C.",
    key_condition: "Validar prueba de concepto con proveedor.",
    value_capture: "ahorro",
    brl: 3,
    technical_milestones: "Mes 1: diseño; Mes 2-3: fabricación; Mes 4-6: instalación y pruebas.",
    financial_milestones: "Payback estimado en 10 meses.",
    return_horizon: 10,
    strategic_alignment: "H2 — Sostenibilidad",
    dbi_raw_text: null,
    dbi_extra: null,
    created_at: "2026-06-12T09:15:00-04:00",
    updated_at: "2026-06-18T16:00:00-04:00",
    evaluation: {
      id: 201,
      status: "in_progress",
      results: {
        score: 78,
        viability: "Alta",
        risk_level: "Medio",
        recommendations: ["Validar temperatura máxima del imán", "Considerar redundancia del sistema"],
      },
      veredicto: null,
      reviewed_at: null,
    },
  },
  {
    id: 103,
    session_id: null,
    user_id: "other-user-id",
    status: "evaluado" as const,
    initiative_code: "INI-2026-003",
    title: "Sistema de gestión predictiva de flota de camiones CAEX",
    initiative_type: "mixta" as const,
    postulation_date: "2026-06-08",
    area: "Mina",
    applicant_name: "Pedro Rojas",
    problem:
      "El mantenimiento reactivo de la flota CAEX genera 30% de tiempo de inactividad no planificado.",
    solution:
      "Plataforma de mantenimiento predictivo con machine learning sobre datos de telemetría existentes.",
    economic_impact: "Reducción de USD 500K/año en costos de mantenimiento y aumento de disponibilidad.",
    trl: 6,
    scalability: "Externa",
    internal_client: "Gerencia Mina",
    external_client: "Otras divisiones de Elecmetal con flota CAEX",
    crl: 6,
    sponsor: "Marcela Vega — Directora de Operaciones Mina",
    internal_team: "Data Science (2) + Ingeniería Mina (4)",
    external_team: "Consultor ML externo",
    estimated_duration: "12 meses",
    main_doubt: "Calidad y completitud de los datos históricos de telemetría.",
    key_condition: "Acceso completo a la base de datos de telemetría de los últimos 3 años.",
    value_capture: "competitividad",
    brl: 5,
    technical_milestones: "Fase 1: data pipeline; Fase 2: modelo ML; Fase 3: integración dashboard.",
    financial_milestones: "ROI proyectado a 24 meses.",
    return_horizon: 24,
    strategic_alignment: "H3 — Transformación Digital",
    dbi_raw_text: null,
    dbi_extra: null,
    created_at: "2026-06-08T11:00:00-04:00",
    updated_at: "2026-06-20T10:30:00-04:00",
    evaluation: {
      id: 202,
      status: "completed",
      results: {
        score: 92,
        viability: "Muy alta",
        risk_level: "Bajo",
        recommendations: [
          "Priorizar para 2027",
          "Considerar patente del modelo predictivo",
          "Evaluar escalamiento a otras operaciones",
        ],
      },
      veredicto: null,
      reviewed_at: "2026-06-20T10:30:00-04:00",
    },
  },
];

export const mockSessions = [
  {
    id: 1,
    user_id: "test-user-id",
    agent_type: "clara" as const,
    status: "active" as const,
    title: "Postulación de mejora en molinos",
    started_at: "2026-06-17T15:30:00-04:00",
    ended_at: null,
    created_at: "2026-06-17T15:30:00-04:00",
    updated_at: "2026-06-17T15:30:00-04:00",
  },
  {
    id: 2,
    user_id: "test-user-id",
    agent_type: "analista_oportunidad" as const,
    status: "active" as const,
    title: null,
    started_at: "2026-06-16T10:00:00-04:00",
    ended_at: null,
    created_at: "2026-06-16T10:00:00-04:00",
    updated_at: "2026-06-16T10:00:00-04:00",
  },
];

export const handlers = [
  // GET /api/v1/me
  http.get(`${API_URL}/api/v1/me`, ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }
    return HttpResponse.json(mockProfile);
  }),

  // GET /api/v1/sessions
  http.get(`${API_URL}/api/v1/sessions`, ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }
    return HttpResponse.json({ data: mockSessions });
  }),

  // POST /api/v1/sessions
  http.post(`${API_URL}/api/v1/sessions`, async ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }
    const body = (await request.json()) as { agent_type: string };
    return HttpResponse.json(
      {
        id: 3,
        user_id: "test-user-id",
        agent_type: body.agent_type,
        status: "active",
        title: null,
        started_at: "2026-06-17T16:00:00-04:00",
        ended_at: null,
        created_at: "2026-06-17T16:00:00-04:00",
        updated_at: "2026-06-17T16:00:00-04:00",
      },
      { status: 201 },
    );
  }),

  // GET /api/v1/sessions/:sessionId/stream — SSE mock
  http.get(`${API_URL}/api/v1/sessions/:sessionId/stream`, ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }

    const url = new URL(request.url);
    const resumeFrom = url.searchParams.get("resume_from");
    const simulateError = url.searchParams.get("simulate_error");

    const allTokens = tokenize(MOCK_CLARA_REPLY);

    // Si es una reconexión, reanudar desde el token indicado
    const startIndex = resumeFrom ? Math.min(Number(resumeFrom), allTokens.length) : 0;
    const tokens = allTokens.slice(startIndex);

    // Si se pide simular error
    const errorAfter = simulateError !== null
      ? Math.min(Number(simulateError), tokens.length)
      : undefined;

    return createSSEResponse(tokens, errorAfter);
  }),

  // GET /api/v1/sessions/:sessionId
  http.get(`${API_URL}/api/v1/sessions/:sessionId`, ({ request, params }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }
    const session = mockSessions.find((s) => s.id === Number(params.sessionId));
    if (!session) {
      return HttpResponse.json(
        { error: { code: "SESSION_NOT_FOUND", message: "La sesión no existe" } },
        { status: 404 },
      );
    }
    return HttpResponse.json(session);
  }),

  // GET /api/v1/sessions/:sessionId/messages
  http.get(`${API_URL}/api/v1/sessions/:sessionId/messages`, ({ request, params }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }
    const sessionMessages = mockMessages.filter(
      (m) => m.session_id === Number(params.sessionId),
    );
    return HttpResponse.json({
      data: sessionMessages,
      pagination: { next_cursor: null, has_more: false },
    });
  }),

  // POST /api/v1/sessions/:sessionId/messages
  http.post(`${API_URL}/api/v1/sessions/:sessionId/messages`, async ({ request, params }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }
    const body = (await request.json()) as { content: string };
    const now = new Date().toISOString();
    const userMsg = {
      id: ++messageIdCounter,
      session_id: Number(params.sessionId),
      role: "user" as const,
      content: body.content,
      metadata: null,
      created_at: now,
    };
    // Con OpenAI real, la respuesta del asistente llega via SSE stream.
    // Solo devolvemos el user_message; el assistant_message se obtiene
    // cuando el frontend refetcha los mensajes tras recibir [DONE].
    return HttpResponse.json(
      { user_message: userMsg },
      { status: 201 },
    );
  }),

  // ─── Initiatives ────────────────────────────────────────────

  // GET /api/v1/initiatives
  http.get(`${API_URL}/api/v1/initiatives`, ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }

    const url = new URL(request.url);
    const statusFilter = url.searchParams.get("status");
    const cursor = url.searchParams.get("cursor");
    const limit = Number(url.searchParams.get("limit") || "20");

    let filtered = mockInitiatives;
    if (statusFilter) {
      filtered = filtered.filter((i) => i.status === statusFilter);
    }

    if (cursor) {
      const cursorId = Number(cursor);
      filtered = filtered.filter((i) => i.id < cursorId);
    }

    const hasMore = filtered.length > limit;
    const data = filtered.slice(0, limit);

    return HttpResponse.json({
      data: data.map(({ evaluation, ...rest }) => rest),
      pagination: {
        next_cursor: data.length > 0 ? data[data.length - 1].id : null,
        has_more: hasMore,
      },
    });
  }),

  // GET /api/v1/initiatives/:id
  http.get(`${API_URL}/api/v1/initiatives/:id`, ({ request, params }) => {
    const auth = request.headers.get("Authorization");
    if (!auth) {
      return HttpResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Token inválido" } },
        { status: 401 },
      );
    }

    const initiative = mockInitiatives.find(
      (i) => i.id === Number(params.id),
    );
    if (!initiative) {
      return HttpResponse.json(
        { error: { code: "INITIATIVE_NOT_FOUND", message: "La iniciativa no existe" } },
        { status: 404 },
      );
    }

    // Simular 403 para iniciativa de otro usuario (a menos que sea directora)
    // En tests usamos el mockProfile con role 'postulante', así que solo
    // permitimos acceso a iniciativas propias
    const userId = request.headers.get("X-Test-User-Id") || "test-user-id";
    if (initiative.user_id !== userId && initiative.id !== 101 && initiative.id !== 102) {
      // Permitir 103 solo si el header lo pide (para tests de directora)
      if (request.headers.get("X-Test-Role") !== "directora") {
        return HttpResponse.json(
          { error: { code: "FORBIDDEN", message: "No tienes acceso a esta iniciativa" } },
          { status: 403 },
        );
      }
    }

    return HttpResponse.json(initiative);
  }),
];
