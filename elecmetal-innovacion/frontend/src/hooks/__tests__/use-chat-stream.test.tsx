import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChatStream } from "../use-chat-stream";
import { createTestQueryClient } from "@/test/test-utils";
import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// Mock getAccessToken para evitar dependencia de Supabase en tests
vi.mock("@/lib/get-token", () => ({
  getAccessToken: vi.fn().mockResolvedValue("fake-token"),
}));

function createWrapper(queryClient?: ReturnType<typeof createTestQueryClient>) {
  const qc = queryClient || createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useChatStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("devuelve el estado inicial correctamente", () => {
    const { result } = renderHook(() => useChatStream(1), {
      wrapper: createWrapper(),
    });

    expect(result.current.streamingMessage).toBeNull();
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.streamError).toBeNull();
    expect(typeof result.current.send).toBe("function");
    expect(typeof result.current.cancelStream).toBe("function");
    expect(typeof result.current.retryStream).toBe("function");
  });

  it("inicia streaming al enviar un mensaje", async () => {
    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useChatStream(1), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.send("Hola Clara");
    });

    // El stream mock SSE puede tardar varios segundos (tokens con delay).
    // Verificamos que el mensaje del usuario se agregó al cache optimistamente.
    const messages = queryClient.getQueryData(["messages", 1]) as Array<unknown>;
    expect(messages).toBeTruthy();
    expect(Array.isArray(messages)).toBe(true);
    expect(messages.length).toBeGreaterThanOrEqual(1);
  });

  it("maneja el envío con error si la API falla", async () => {
    // Importamos MSW para simular un error de red en el endpoint de mensajes
    const { http, HttpResponse } = await import("msw");
    const { server } = await import("@/test/mocks/server");

    const API_URL = "http://localhost:8000";
    server.use(
      http.post(`${API_URL}/api/v1/sessions/1/messages`, () => {
        return HttpResponse.json(
          { error: { code: "SERVER_ERROR", message: "Error interno" } },
          { status: 500 },
        );
      }),
    );

    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useChatStream(1), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.send("Hola Clara");
    });

    // Debe mostrar error de envío
    expect(result.current.streamError).toBe("Error al enviar el mensaje. Intenta de nuevo.");
    expect(result.current.isStreaming).toBe(false);
  });

  it("cancela el stream activo", async () => {
    const { result } = renderHook(() => useChatStream(1), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.cancelStream();
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.streamingMessage).toBeNull();
    expect(result.current.streamError).toBeNull();
  });
});
