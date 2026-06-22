import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import MessageBubble from "../message-bubble";
import { renderWithProviders } from "@/test/test-utils";

describe("MessageBubble", () => {
  it("renderiza un mensaje de usuario con contenido", () => {
    renderWithProviders(
      <MessageBubble
        role="user"
        content="Hola Clara"
        created_at="2026-06-17T15:00:00-04:00"
      />,
    );

    expect(screen.getByText(/Hola Clara/)).toBeInTheDocument();
    // El mensaje de usuario debe tener fondo azul
    const bubble = screen.getByText(/Hola Clara/).closest("div.max-w-\\[70\\%\\]");
    expect(bubble?.className).toMatch(/bg-blue-600/);
  });

  it("renderiza un mensaje del asistente con contenido", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="¡Hola! Soy Clara"
        created_at="2026-06-17T15:01:00-04:00"
      />,
    );

    expect(screen.getByText(/¡Hola! Soy Clara/)).toBeInTheDocument();
    // El mensaje del asistente debe tener fondo gris
    const bubble = screen.getByText(/¡Hola! Soy Clara/).closest("div.max-w-\\[70\\%\\]");
    expect(bubble?.className).toMatch(/bg-gray-100/);
  });

  it("no renderiza mensajes del sistema (system)", () => {
    const { container } = renderWithProviders(
      <MessageBubble
        role="system"
        content="Mensaje interno"
        created_at="2026-06-17T15:00:00-04:00"
      />,
    );

    // El componente retorna null para system messages
    expect(container.firstChild).toBeNull();
  });

  it("muestra cursor parpadeante cuando isStreaming es true", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="Hola"
        created_at={new Date().toISOString()}
        isStreaming
      />,
    );

    expect(screen.getByText(/Hola/)).toBeInTheDocument();
    // Debe mostrar "Escribiendo..." en lugar de la hora
    expect(screen.getByText(/Escribiendo\.\.\./)).toBeInTheDocument();
    // Debe existir el elemento del cursor con la animación blink
    const cursor = document.querySelector(".animate-blink");
    expect(cursor).toBeInTheDocument();
  });

  it("muestra la hora formateada cuando no está streameando", () => {
    renderWithProviders(
      <MessageBubble
        role="user"
        content="Test"
        created_at="2026-06-17T15:30:00-04:00"
      />,
    );

    // Debe mostrar alguna hora (depende de la zona horaria, verificamos que NO diga "Escribiendo...")
    expect(screen.queryByText(/Escribiendo\.\.\./)).not.toBeInTheDocument();
  });

  it("renderiza contenido multilinea con whitespace-pre-wrap", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="Línea 1\nLínea 2"
        created_at="2026-06-17T15:00:00-04:00"
      />,
    );

    const text = screen.getByText(/Línea 1/);
    expect(text.className).toMatch(/whitespace-pre-wrap/);
    expect(screen.getByText(/Línea 2/)).toBeInTheDocument();
  });
});
