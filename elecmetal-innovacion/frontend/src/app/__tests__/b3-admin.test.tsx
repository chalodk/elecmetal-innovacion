/**
 * B3 tests — Panel Directora unificado (InitiativeCard + acciones de Jorge).
 * MSW se detiene porque estos tests mockean fetch manualmente.
 */
import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { server } from "@/test/mocks/server";

beforeAll(() => server.close());
afterAll(() => server.listen({ onUnhandledRequest: "bypass" }));

const mockFetch = vi.fn();
global.fetch = mockFetch;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), prefetch: vi.fn() }),
  useParams: () => ({ id: "1" }),
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

import AdminPage from "@/app/dashboard/admin/page";

const MOCK_INITIATIVE = {
  id: 1, initiative_code: "INI-2026-001", title: "Mantenimiento predictivo",
  status: "notificado", initiative_type: "interna", applicant_name: "Jorge Melian",
  area: "Mina", postulation_date: "2026-06-15T00:00:00", created_at: "2026-06-15T00:00:00",
};

describe("B3 | Panel de directora", () => {
  beforeEach(() => { mockFetch.mockReset(); getQueryClient().clear(); });

  it("renderiza datos de iniciativa en la lista", async () => {
    mockUrls({
      "/initiatives": { data: { data: [MOCK_INITIATIVE], pagination: { has_more: false, next_cursor: null } } },
    });

    render(<AdminPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByText("Mantenimiento predictivo")).toBeInTheDocument(); });
    expect(screen.getByText("INI-2026-001")).toBeInTheDocument();
  });

  it("muestra boton Enviar a evaluacion para notificado", async () => {
    mockUrls({
      "/initiatives": { data: { data: [MOCK_INITIATIVE], pagination: { has_more: false, next_cursor: null } } },
    });

    render(<AdminPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByText(/Enviar a evaluacion/)).toBeInTheDocument(); });
  });

  it("muestra estado vacio cuando no hay iniciativas", async () => {
    mockUrls({
      "/initiatives": { data: { data: [], pagination: { has_more: false, next_cursor: null } } },
    });

    render(<AdminPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByText(/No hay iniciativas/)).toBeInTheDocument(); });
  });

  it("muestra estado de carga al iniciar", () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    render(<AdminPage />, { wrapper: TestWrapper });
    expect(screen.getByText(/Iniciativas/)).toBeInTheDocument();
  });
});
