/**
 * Cliente SSE genérico para leer streams de tokens desde el backend.
 * No depende de React — se puede usar desde cualquier entorno JS.
 *
 * Formato esperado del stream (SSE estándar):
 *   data: {"token": "Hola"}
 *   data: {"token": " mundo"}
 *   data: [DONE]
 *
 * Cada línea `data:` contiene un JSON con el campo `token` (string).
 * El stream termina cuando se recibe `data: [DONE]`.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SSEToken {
  token: string;
}

export interface SSEStreamResult {
  /** Stream de tokens parseados */
  stream: ReadableStream<string>;
  /** Aborta la conexión */
  abort: () => void;
}

function parseSSELine(line: string): string | null {
  if (!line.startsWith("data: ")) return null;
  const payload = line.slice(6).trim();
  if (payload === "[DONE]") return "__DONE__";
  try {
    const parsed: SSEToken = JSON.parse(payload);
    return parsed.token ?? null;
  } catch {
    return null;
  }
}

export function createSSEStream(
  sessionId: number,
  token: string,
  resumeFrom?: number,
): SSEStreamResult {
  const controller = new AbortController();

  const params = new URLSearchParams();
  if (resumeFrom) params.set("resume_from", String(resumeFrom));

  const qs = params.toString();
  const url = `${API_URL}/api/v1/sessions/${sessionId}/stream${qs ? `?${qs}` : ""}`;

  const stream = new ReadableStream<string>({
    async start(streamController) {
      try {
        const response = await fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "text/event-stream",
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          const errorText = await response.text().catch(() => "");
          streamController.error(
            new Error(`SSE connection failed: ${response.status} ${errorText}`),
          );
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          streamController.error(new Error("No response body"));
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // La última línea puede estar incompleta
          buffer = lines.pop() || "";

          for (const line of lines) {
            const result = parseSSELine(line.trim());
            if (result === "__DONE__") {
              streamController.close();
              return;
            }
            if (result !== null) {
              streamController.enqueue(result);
            }
          }
        }

        // Procesar el buffer remanente
        if (buffer.trim()) {
          const result = parseSSELine(buffer.trim());
          if (result === "__DONE__") {
            streamController.close();
            return;
          }
          if (result !== null) {
            streamController.enqueue(result);
          }
        }

        streamController.close();
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          streamController.close();
          return;
        }
        streamController.error(err);
      }
    },
  });

  return {
    stream,
    abort: () => controller.abort(),
  };
}
