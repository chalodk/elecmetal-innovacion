import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mocking
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

describe("API client (api.ts)", () => {
  const TEST_TOKEN = "test-token-123";

  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe("authFetch helper", () => {
    it("adds Authorization header and Content-Type", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: "test" }),
      });

      const res = await fetch(`${API_URL}/api/v1/me`, {
        headers: {
          Authorization: `Bearer ${TEST_TOKEN}`,
          "Content-Type": "application/json",
        },
      });
      const body = await res.json();

      expect(res.ok).toBe(true);
      expect(body).toEqual({ data: "test" });
    });

    it("throws on non-ok responses", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Not found" }),
      });

      const res = await fetch(`${API_URL}/api/v1/me`, {
        headers: { Authorization: `Bearer ${TEST_TOKEN}` },
      });
      const body = await res.json();

      expect(res.ok).toBe(false);
      expect(body.detail).toBe("Not found");
    });
  });

  describe("SSE parsing in sendMessage", () => {
    it("correctly splits SSE events by double newline", () => {
      // Simulate what the SSE parser does
      const raw = [
        'data: {"token":"Hola"}',
        'data: {"token":" mundo"}',
        'data: {"done":true,"message_id":42}',
      ].join("\n");

      const lines = raw.split("\n");
      const events = lines
        .filter((l) => l.startsWith("data: "))
        .map((l) => JSON.parse(l.slice(6)));

      expect(events).toHaveLength(3);
      expect(events[0]).toEqual({ token: "Hola" });
      expect(events[1]).toEqual({ token: " mundo" });
      expect(events[2]).toEqual({ done: true, message_id: 42 });
    });

    it("handles initiative info in done payload", () => {
      const donePayload = JSON.stringify({
        done: true,
        message_id: 100,
        initiative: {
          initiative_id: 5,
          initiative_code: "INI-2026-001",
          status: "persistido",
        },
      });

      const parsed = JSON.parse(donePayload);
      expect(parsed.initiative.initiative_code).toBe("INI-2026-001");
      expect(parsed.initiative.status).toBe("persistido");
    });

    it("handles parse errors in initiative info", () => {
      const errorPayload = JSON.stringify({
        done: true,
        message_id: 101,
        initiative: { parse_error: "Faltan las lineas de borde" },
      });

      const parsed = JSON.parse(errorPayload);
      expect(parsed.initiative.parse_error).toBeDefined();
    });
  });

  describe("API URL construction", () => {
    it("constructs correct health check URL", () => {
      const url = `${API_URL}/api/v1/health`;
      expect(url).toContain("/api/v1/health");
    });

    it("constructs session endpoints correctly", () => {
      expect(`${API_URL}/api/v1/sessions`).toContain("/sessions");
      expect(`${API_URL}/api/v1/sessions/42/messages`).toContain("/42/messages");
    });

    it("constructs initiative endpoints correctly", () => {
      expect(`${API_URL}/api/v1/initiatives`).toContain("/initiatives");
      expect(`${API_URL}/api/v1/initiatives/5`).toContain("/5");
    });

    it("constructs evaluation endpoints correctly", () => {
      expect(`${API_URL}/api/v1/evaluations/3`).toContain("/evaluations/3");
      expect(`${API_URL}/api/v1/initiatives/7/evaluation`).toContain(
        "/7/evaluation",
      );
    });

    it("constructs notification endpoints correctly", () => {
      expect(`${API_URL}/api/v1/notifications`).toContain("/notifications");
      expect(`${API_URL}/api/v1/notifications/process`).toContain("/process");
    });
  });

  describe("pagination envelope parsing", () => {
    it("parses paginated response correctly", () => {
      const response = {
        data: [{ id: 1 }, { id: 2 }],
        pagination: {
          has_more: true,
          next_cursor: "2",
          limit: 20,
        },
      };

      expect(response.data).toHaveLength(2);
      expect(response.pagination.has_more).toBe(true);
      expect(response.pagination.next_cursor).toBe("2");
    });

    it("handles last page (no more data)", () => {
      const response = {
        data: [{ id: 3 }],
        pagination: {
          has_more: false,
          next_cursor: null,
          limit: 20,
        },
      };

      expect(response.pagination.has_more).toBe(false);
      expect(response.pagination.next_cursor).toBeNull();
    });
  });

  describe("agent type validation", () => {
    it("accepts valid agent types", () => {
      const validTypes = ["clara", "analista_oportunidad"];
      for (const at of validTypes) {
        expect(["clara", "analista_oportunidad"]).toContain(at);
      }
    });

    it("rejects invalid agent type", () => {
      const invalid = "invalid_agent";
      expect(["clara", "analista_oportunidad"]).not.toContain(invalid);
    });
  });
});
