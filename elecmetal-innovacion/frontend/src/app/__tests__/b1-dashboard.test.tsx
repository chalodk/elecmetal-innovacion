/**
 * B1 tests — Dashboard page unificada (ProfileCard + WelcomeState + StatusBadge).
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
  useParams: () => ({ sessionId: "1" }),
  redirect: vi.fn(),
  useSearchParams: () => ({ get: () => null }),
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

import DashboardPage from "@/app/dashboard/page";

describe("B1 | Dashboard page", () => {
  beforeEach(() => { mockFetch.mockReset(); getQueryClient().clear(); });

  it("muestra perfil e iniciativas al cargar", async () => {
    mockUrls({
      "/me": { data: { id: "u1", full_name: "Jorge Melian", role: "postulante" } },
      "/sessions": { data: { data: [], pagination: { has_more: false } } },
      "/initiatives": { data: { data: [{ id: 1, initiative_code: "INI-2026-001", title: "Mantenimiento predictivo", status: "notificado", initiative_type: "interna", created_at: "2026-06-15T00:00:00" }], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });

    render(<DashboardPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByText("Jorge Melian")).toBeInTheDocument(); });
    expect(screen.getByText(/Rol:/)).toBeInTheDocument();
    expect(screen.getByText("INI-2026-001")).toBeInTheDocument();
  });

  it("muestra estado vacio sin iniciativas", async () => {
    mockUrls({
      "/me": { data: { id: "u1", full_name: "Test", role: "postulante" } },
      "/sessions": { data: { data: [], pagination: { has_more: false } } },
      "/initiatives": { data: { data: [], pagination: { has_more: false, next_cursor: null, limit: 20 } } },
    });

    render(<DashboardPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByText(/Crea una sesión/)).toBeInTheDocument(); });
  });

  it("maneja error de API", async () => {
    mockUrls({
      "/me": { data: { id: "u1", full_name: "Test", role: "postulante" } },
      "/sessions": { data: { data: [], pagination: { has_more: false } } },
      "/initiatives": { data: { error: { message: "DB error" } }, ok: false },
    });

    render(<DashboardPage />, { wrapper: TestWrapper });

    await waitFor(() => { expect(screen.getByText("Test")).toBeInTheDocument(); });
  });
});
