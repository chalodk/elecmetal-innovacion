import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import type { Session } from "@/lib/types";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock server action
vi.mock("@/app/dashboard/actions", () => ({
  signOut: vi.fn(),
}));

// Mock the hooks
vi.mock("@/hooks/use-sessions", () => ({
  useSessions: vi.fn(),
  useCreateSession: vi.fn(),
  SESSIONS_KEY: ["sessions"],
}));

import { useSessions, useCreateSession } from "@/hooks/use-sessions";
import Sidebar from "../sidebar";

function mockUseSessions(overrides: {
  data?: Session[];
  isLoading?: boolean;
  isError?: boolean;
}) {
  (useSessions as ReturnType<typeof vi.fn>).mockReturnValue({
    data: overrides.data,
    isLoading: overrides.isLoading ?? false,
    isError: overrides.isError ?? false,
    refetch: vi.fn(),
  });
}

function mockUseCreateSession() {
  const mutateAsync = vi.fn().mockResolvedValue({ id: 3, agent_type: "clara", status: "active" });
  (useCreateSession as ReturnType<typeof vi.fn>).mockReturnValue({
    mutateAsync,
    isPending: false,
    isError: false,
  });
  return { mutateAsync };
}

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCreateSession();
  });

  it("muestra skeletons durante loading", () => {
    mockUseSessions({ isLoading: true });
    renderWithProviders(<Sidebar user={{ email: "test@elecmetal.cl", role: null }} />);

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("muestra mensaje cuando no hay sesiones", () => {
    mockUseSessions({ data: [] });
    renderWithProviders(<Sidebar user={{ email: "test@elecmetal.cl", role: null }} />);

    expect(screen.getByText(/No hay sesiones todavía/)).toBeInTheDocument();
  });

  it("muestra mensaje de error con botón reintentar", () => {
    mockUseSessions({ isError: true });
    renderWithProviders(<Sidebar user={{ email: "test@elecmetal.cl", role: null }} />);

    expect(screen.getByText(/Error al cargar sesiones/)).toBeInTheDocument();
    expect(screen.getByText(/Reintentar/)).toBeInTheDocument();
  });

  it("muestra lista de sesiones", () => {
    mockUseSessions({
      data: [
        {
          id: 1,
          user_id: "u1",
          agent_type: "clara",
          status: "active",
          title: "Test session",
          started_at: "2026-06-17T15:30:00-04:00",
          ended_at: null,
          created_at: "2026-06-17T15:30:00-04:00",
          updated_at: "2026-06-17T15:30:00-04:00",
        },
      ],
    });
    renderWithProviders(<Sidebar user={{ email: "test@elecmetal.cl", role: null }} />);

    expect(screen.getByText(/Clara/)).toBeInTheDocument();
    expect(screen.getByText(/Test session/)).toBeInTheDocument();
  });

  it("abre el modal al hacer clic en Nueva sesión", () => {
    mockUseSessions({ data: [] });
    renderWithProviders(<Sidebar user={{ email: "test@elecmetal.cl", role: null }} />);

    fireEvent.click(screen.getByText(/Nueva sesión/));
    expect(screen.getByText(/¿Qué tipo de sesión quieres crear?/)).toBeInTheDocument();
  });
});
