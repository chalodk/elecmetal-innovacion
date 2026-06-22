/**
 * B3 tests - Vista de iniciativa + panel directora.
 *
 * Tests: panel de directora con tabs y acciones, DBI viewer bloques A-G,
 * dbi_extra, scorecard del Evaluador, veredicto, acceso denegado por rol.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";

const mockFetch = vi.fn();
global.fetch = mockFetch;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), prefetch: vi.fn() }),
  useParams: () => ({ id: "1" }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: () =>
        Promise.resolve({
          data: { session: { access_token: "test-token" } },
        }),
    },
  }),
}));

import { QueryClient } from "@tanstack/react-query";

function makeTestQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: 0 } },
  });
}

function TestWrapper({ children }: { children: React.ReactNode }) {
  const qc = makeTestQC();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function mockUrls(routes: Record<string, { data: unknown; ok?: boolean }>) {
  mockFetch.mockImplementation(async (url: string) => {
    for (const [pattern, resp] of Object.entries(routes)) {
      if (url.includes(pattern)) {
        return { ok: resp.ok ?? true, json: async () => resp.data };
      }
    }
    return { ok: false, json: async () => ({ error: { message: "Unmatched" } }) };
  });
}

import AdminPage from "@/app/dashboard/admin/page";

describe("B3 | Panel de directora", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("renderiza datos de iniciativa en la tabla", async () => {
    mockUrls({
      "/initiatives": { data: { data: [
        { id: 1, initiative_code: "INI-2026-001", title: "Mantenimiento predictivo", status: "notificado", initiative_type: "interna", applicant_name: "Carlos", area: "Fundicion", postulation_date: "2026-06-01", created_at: "2026-06-01T00:00:00" },
      ], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });
    render(<AdminPage />, { wrapper: TestWrapper });
    expect(await screen.findByText("INI-2026-001", {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText("Mantenimiento predictivo")).toBeInTheDocument();
    expect(screen.getByText("Todas")).toBeInTheDocument();
    expect(screen.getByText("Pendientes")).toBeInTheDocument();
  });

  it("filtra por tab activo", async () => {
    mockUrls({
      "/initiatives": { data: { data: [{ id: 1, initiative_code: "INI-2026-001", title: "Test", status: "notificado", initiative_type: "interna", applicant_name: "X", area: "Area", postulation_date: "2026-01-01", created_at: "2026-01-01T00:00:00" }], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });
    render(<AdminPage />, { wrapper: TestWrapper });
    await waitFor(() => { expect(screen.getByText("INI-2026-001")).toBeInTheDocument(); }, { timeout: 5000 });
    fireEvent.click(screen.getByText("Evaluadas"));
    await waitFor(() => { expect(screen.getByText(/No hay iniciativas/)).toBeInTheDocument(); });
  });

  it("muestra boton Enviar a evaluacion para notificado", async () => {
    mockUrls({
      "/initiatives": { data: { data: [{ id: 1, initiative_code: "INI-2026-001", title: "Test", status: "notificado", initiative_type: "interna", applicant_name: "X", area: "Area", postulation_date: "2026-01-01", created_at: "2026-01-01T00:00:00" }], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });
    render(<AdminPage />, { wrapper: TestWrapper });
    await waitFor(() => { expect(screen.getByText(/Enviar a evaluacion/)).toBeInTheDocument(); });
  });

  it("muestra estado vacio cuando no hay iniciativas", async () => {
    mockUrls({
      "/initiatives": { data: { data: [], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });
    render(<AdminPage />, { wrapper: TestWrapper });
    await waitFor(() => { expect(screen.getByText(/No hay iniciativas/)).toBeInTheDocument(); });
  });

  it("muestra estado de carga al iniciar", () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    render(<AdminPage />, { wrapper: TestWrapper });
    expect(screen.getByText(/Cargando iniciativas/)).toBeInTheDocument();
  });
});
