import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useInitiatives } from "../use-initiatives";
import { createTestQueryClient } from "@/test/test-utils";

// Mock getAccessToken para evitar dependencia de Supabase en tests
vi.mock("@/lib/get-token", () => ({
  getAccessToken: vi.fn().mockResolvedValue("fake-token"),
}));

function createWrapper() {
  const qc = createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useInitiatives", () => {
  it("devuelve datos de iniciativas desde MSW", async () => {
    const { result } = renderHook(() => useInitiatives(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.data).toBeInstanceOf(Array);
    expect(result.current.data!.data.length).toBeGreaterThan(0);
    expect(result.current.data!.data[0]).toHaveProperty("initiative_code");
    expect(result.current.data!.data[0]).toHaveProperty("status");
    expect(result.current.data!.data[0]).toHaveProperty("title");
  });

  it("filtra por status cuando se pasa el parametro", async () => {
    const { result } = renderHook(
      () => useInitiatives({ status: "notificado" }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const initiatives = result.current.data!.data;
    for (const init of initiatives) {
      expect(init.status).toBe("notificado");
    }
  });

  it("devuelve paginacion", async () => {
    const { result } = renderHook(() => useInitiatives({ limit: 2 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.pagination).toBeDefined();
    expect(typeof result.current.data?.pagination.has_more).toBe("boolean");
  });
});
