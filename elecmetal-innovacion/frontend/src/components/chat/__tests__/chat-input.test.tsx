import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import ChatInput from "../chat-input";
import { renderWithProviders } from "@/test/test-utils";

describe("ChatInput", () => {
  it("renderiza el input y el botón de enviar", () => {
    renderWithProviders(<ChatInput onSend={vi.fn()} />);

    expect(screen.getByPlaceholderText("Escribe tu mensaje...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeInTheDocument();
  });

  it("envía el mensaje al hacer clic en Enviar", () => {
    const onSend = vi.fn();

    renderWithProviders(<ChatInput onSend={onSend} />);

    const input = screen.getByPlaceholderText("Escribe tu mensaje...");
    fireEvent.change(input, { target: { value: "Hola Clara" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(onSend).toHaveBeenCalledWith("Hola Clara");
  });

  it("no envía si el input está vacío", () => {
    const onSend = vi.fn();

    renderWithProviders(<ChatInput onSend={onSend} />);

    const button = screen.getByRole("button", { name: "Enviar" });
    expect(button).toBeDisabled();

    fireEvent.click(button);
    expect(onSend).not.toHaveBeenCalled();
  });

  it("limpia el input después de enviar", () => {
    const onSend = vi.fn();

    renderWithProviders(<ChatInput onSend={onSend} />);

    const input = screen.getByPlaceholderText("Escribe tu mensaje...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Hola" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(input.value).toBe("");
  });

  it("deshabilita el input y muestra 'Clara está escribiendo...' durante streaming", () => {
    renderWithProviders(<ChatInput onSend={vi.fn()} isStreaming />);

    const input = screen.getByPlaceholderText("Clara está escribiendo...");
    expect(input).toBeDisabled();

    const button = screen.getByRole("button", { name: "Enviando..." });
    expect(button).toBeDisabled();
  });

  it("deshabilita el input cuando disabled es true", () => {
    renderWithProviders(<ChatInput onSend={vi.fn()} disabled />);

    const input = screen.getByPlaceholderText("Escribe tu mensaje...");
    expect(input).toBeDisabled();
  });

  it("no envía cuando está disabled y streaming simultáneamente", () => {
    const onSend = vi.fn();

    renderWithProviders(<ChatInput onSend={onSend} disabled isStreaming />);

    const input = screen.getByPlaceholderText("Clara está escribiendo...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Hola" } });

    expect(screen.getByRole("button", { name: "Enviando..." })).toBeDisabled();
  });
});
