/**
 * B2 tests - UI de chat + streaming SSE.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";

const mockFetch = vi.fn();
global.fetch = mockFetch;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), prefetch: vi.fn() }),
  useParams: () => ({ sessionId: "1" }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { getSession: () => Promise.resolve({ data: { session: { access_token: "test-token" } } }) },
  }),
}));

function TestWrapper({ children }: { children: React.ReactNode }) {
  const qc = getQueryClient(); qc.clear();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function mockUrls(routes: Record<string, { data: unknown; ok?: boolean }>) {
  mockFetch.mockImplementation(async (url: string) => {
    for (const [pattern, resp] of Object.entries(routes)) {
      if (url.includes(pattern)) {
        return { ok: resp.ok ?? true, json: async () => resp.data };
      }
    }
    return { ok: false, json: async () => ({ error: { message: "Unmatched: " + url } }) };
  });
}

import ChatPage from "@/app/dashboard/chat/[sessionId]/page";

describe("B2 | Chat page", () => {
  beforeEach(() => { mockFetch.mockReset(); getQueryClient().clear(); });

  it("renderiza historial de mensajes", async () => {
    mockUrls({
      "/messages": { data: { data: [
        { id: 1, session_id: 1, role: "user", content: "Hola Clara", metadata: null, created_at: "2026-01-01T00:00:00" },
        { id: 2, session_id: 1, role: "assistant", content: "Hola! Soy Clara.", metadata: null, created_at: "2026-01-01T00:00:01" },
      ], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });

    render(<ChatPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByText("Hola Clara")).toBeInTheDocument(); });
    expect(screen.getByText("Hola! Soy Clara.")).toBeInTheDocument();
  });

  it("muestra placeholder sin mensajes", async () => {
    mockUrls({
      "/messages": { data: { data: [], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });

    render(<ChatPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByText(/Envia tu primer mensaje/)).toBeInTheDocument(); });
  });

  it("input vacio deshabilita boton Enviar", async () => {
    mockUrls({
      "/messages": { data: { data: [], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });

    render(<ChatPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByPlaceholderText(/Escribe tu mensaje/)).toBeInTheDocument(); });
    expect(screen.getByRole("button", { name: /Enviar/ })).toBeDisabled();
  });

  it("habilita boton al escribir", async () => {
    mockUrls({
      "/messages": { data: { data: [], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });

    render(<ChatPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByPlaceholderText(/Escribe tu mensaje/)).toBeInTheDocument(); });
    fireEvent.change(screen.getByPlaceholderText(/Escribe tu mensaje/), { target: { value: "Mi idea" } });
    expect(screen.getByRole("button", { name: /Enviar/ })).not.toBeDisabled();
  });

  it("muestra error si falla carga", async () => {
    mockUrls({
      "/messages": { data: { error: { message: "Sesion no encontrada" } }, ok: false },
    });

    render(<ChatPage />, { wrapper: TestWrapper });

    await waitFor(
      () => { expect(screen.getByText(/Error al cargar la sesion/)).toBeInTheDocument(); },
      { timeout: 5000 },
    );
    expect(screen.getByText("Sesion no encontrada")).toBeInTheDocument();
  });

  it("muestra carga al iniciar", () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    render(<ChatPage />, { wrapper: TestWrapper });
    expect(screen.getByText(/Cargando conversacion/)).toBeInTheDocument();
  });
});

describe("B2 | SSE parsing", () => {
  it("extrae tokens de eventos SSE", () => {
    const raw = ['data: {"token":"Hola"}', 'data: {"token":" mundo"}', 'data: {"done":true,"message_id":42}'].join("\n");
    const events = raw.split("\n").filter((l) => l.startsWith("data: ")).map((l) => JSON.parse(l.slice(6)));
    expect(events).toHaveLength(3);
    expect(events[0]).toEqual({ token: "Hola" });
    expect(events[2]).toEqual({ done: true, message_id: 42 });
  });

  it("maneja iniciativa en payload done", () => {
    const p = { done: true, initiative: { initiative_id: 5, initiative_code: "INI-2026-001", status: "persistido" } };
    expect(p.initiative.initiative_code).toBe("INI-2026-001");
  });

  it("maneja error de parseo", () => {
    const p = { done: true, initiative: { parse_error: "Faltan lineas" } };
    expect(p.initiative.parse_error).toBeDefined();
  });

  it("ignora lineas que no son data:", () => {
    const events = ["event: msg", 'data: {"token":"ok"}', ""].join("\n")
      .split("\n").filter((l) => l.startsWith("data: ")).map((l) => JSON.parse(l.slice(6)));
    expect(events).toHaveLength(1);
  });

  it("concatena tokens para typewriter", () => {
    expect(["Hola", " como", " estas", "?"].join("")).toBe("Hola como estas?");
  });
});
