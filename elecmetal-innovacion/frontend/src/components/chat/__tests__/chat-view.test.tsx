import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import ChatView from "../chat-view";
import { renderWithProviders } from "@/test/test-utils";

// Mockeamos los hooks que usa ChatView
const mockSession = {
  id: 1,
  user_id: "test-user-id",
  agent_type: "clara" as const,
  status: "active" as const,
  title: "Sesión de prueba",
  started_at: "2026-06-17T15:00:00-04:00",
  ended_at: null,
  created_at: "2026-06-17T15:00:00-04:00",
  updated_at: "2026-06-17T15:00:00-04:00",
};

const mockMessages = [
  {
    id: 1,
    session_id: 1,
    role: "user" as const,
    content: "Hola Clara",
    metadata: null,
    created_at: "2026-06-17T15:30:00-04:00",
  },
  {
    id: 2,
    session_id: 1,
    role: "assistant" as const,
    content: "¡Hola! ¿En qué puedo ayudarte?",
    metadata: null,
    created_at: "2026-06-17T15:30:30-04:00",
  },
];

// Valores por defecto
const defaultUseSession = {
  data: mockSession,
  isLoading: false,
  isError: false,
  error: null,
};

const defaultUseMessages = {
  data: mockMessages,
  isLoading: false,
  isError: false,
  refetch: vi.fn(),
};

const defaultUseChatStream = {
  streamingMessage: null,
  isStreaming: false,
  streamError: null,
  send: vi.fn(),
  cancelStream: vi.fn(),
  retryStream: vi.fn(),
};

vi.mock("@/hooks/use-session", () => ({
  useSession: vi.fn(() => defaultUseSession),
}));

vi.mock("@/hooks/use-messages", () => ({
  useMessages: vi.fn(() => defaultUseMessages),
  MESSAGES_KEY: (id: number) => ["messages", id] as const,
}));

vi.mock("@/hooks/use-chat-stream", () => ({
  useChatStream: vi.fn(() => defaultUseChatStream),
}));

describe("ChatView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Restaurar valores default después de cada test
    setSessionMock(defaultUseSession);
    setMessagesMock(defaultUseMessages);
    setChatStreamMock(defaultUseChatStream);
  });

  // Helpers para cambiar mocks por test
  async function setSessionMock(overrides: Partial<typeof defaultUseSession>) {
    const { useSession } = await import("@/hooks/use-session");
    vi.mocked(useSession).mockReturnValue({ ...defaultUseSession, ...overrides } as ReturnType<typeof useSession>);
  }

  async function setMessagesMock(overrides: Partial<typeof defaultUseMessages>) {
    const { useMessages } = await import("@/hooks/use-messages");
    vi.mocked(useMessages).mockReturnValue({ ...defaultUseMessages, ...overrides } as ReturnType<typeof useMessages>);
  }

  async function setChatStreamMock(overrides: Partial<typeof defaultUseChatStream>) {
    const { useChatStream } = await import("@/hooks/use-chat-stream");
    vi.mocked(useChatStream).mockReturnValue({ ...defaultUseChatStream, ...overrides } as ReturnType<typeof useChatStream>);
  }

  it("renderiza el nombre del agente y el título de la sesión", () => {
    renderWithProviders(<ChatView sessionId={1} />);

    expect(screen.getByText("Clara")).toBeInTheDocument();
    expect(screen.getByText("Sesión de prueba")).toBeInTheDocument();
  });

  it("muestra 'Analista de Oportunidad' cuando el agente es analista_oportunidad", async () => {
    await setSessionMock({
      data: { ...mockSession, agent_type: "analista_oportunidad" },
    });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(screen.getByText("Analista de Oportunidad")).toBeInTheDocument();
  });

  it("muestra el mensaje de 'sin mensajes' cuando no hay historial ni streaming", async () => {
    await setMessagesMock({ data: [] });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(
      screen.getByText("No hay mensajes todavía. Envía el primero para comenzar."),
    ).toBeInTheDocument();
  });

  it("muestra error de sesión 403 con mensaje de acceso denegado", async () => {
    await setSessionMock({
      data: undefined,
      isError: true,
      error: { status: 403, message: "No tienes acceso" },
    });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(screen.getByText("No tienes acceso a esta sesión")).toBeInTheDocument();
  });

  it("muestra error de sesión 404 con mensaje de no encontrada", async () => {
    await setSessionMock({
      data: undefined,
      isError: true,
      error: { status: 404, message: "No existe" },
    });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(
      screen.getByText("La sesión no existe o fue eliminada"),
    ).toBeInTheDocument();
  });

  it("muestra el indicador de typing cuando está streameando sin contenido", async () => {
    await setChatStreamMock({
      isStreaming: true,
      streamingMessage: null,
    });

    renderWithProviders(<ChatView sessionId={1} />);

    // Verificar que hay 3 dots de typing (spans con animate-bounce)
    const dots = document.querySelectorAll(".animate-bounce");
    expect(dots.length).toBe(3);
  });

  it("muestra el contenido streameando en la lista de mensajes", async () => {
    await setChatStreamMock({
      isStreaming: true,
      streamingMessage: "Hola, soy Clara y estoy",
    });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(screen.getByText("Hola, soy Clara y estoy")).toBeInTheDocument();
    expect(screen.getByText("Escribiendo...")).toBeInTheDocument();
  });

  it("muestra el banner de sesión cerrada cuando no está activa", async () => {
    await setSessionMock({
      data: { ...mockSession, status: "completed" },
    });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(
      screen.getByText("Esta sesión está cerrada. No se pueden enviar nuevos mensajes."),
    ).toBeInTheDocument();
  });

  it("muestra error de stream con botón de reintentar", async () => {
    await setChatStreamMock({
      isStreaming: false,
      streamError: "Error de conexión con Clara. Verifica tu internet e intenta de nuevo.",
    });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(
      screen.getByText("Error de conexión con Clara. Verifica tu internet e intenta de nuevo."),
    ).toBeInTheDocument();
    expect(screen.getByText("Reintentar")).toBeInTheDocument();
  });

  it("no muestra el botón de reintentar durante reconexión automática", async () => {
    await setChatStreamMock({
      isStreaming: false,
      streamError: "Reconectando en 2s... (intento 1/3)",
    });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(
      screen.getByText("Reconectando en 2s... (intento 1/3)"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Reintentar")).not.toBeInTheDocument();
  });

  it("muestra el error de carga de mensajes con botón reintentar", async () => {
    const mockRefetch = vi.fn();
    await setMessagesMock({
      data: [],
      isError: true,
      refetch: mockRefetch,
    });

    renderWithProviders(<ChatView sessionId={1} />);

    expect(screen.getByText("Error al cargar los mensajes")).toBeInTheDocument();
  });
});
