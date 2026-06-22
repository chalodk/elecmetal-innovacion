import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InitiativeStatusBadge from "../initiative-status-badge";
import type { InitiativeStatus } from "@/lib/types";

describe("InitiativeStatusBadge", () => {
  it("muestra 'DBI Generado' para estado dbi_generado", () => {
    render(<InitiativeStatusBadge status="dbi_generado" />);
    expect(screen.getByText("DBI Generado")).toBeInTheDocument();
  });

  it("muestra 'Persistido' para estado persistido", () => {
    render(<InitiativeStatusBadge status="persistido" />);
    expect(screen.getByText("Persistido")).toBeInTheDocument();
  });

  it("muestra 'Notificado' para estado notificado", () => {
    render(<InitiativeStatusBadge status="notificado" />);
    expect(screen.getByText("Notificado")).toBeInTheDocument();
  });

  it("muestra 'En Evaluación' para estado en_evaluacion", () => {
    render(<InitiativeStatusBadge status="en_evaluacion" />);
    expect(screen.getByText("En Evaluación")).toBeInTheDocument();
  });

  it("muestra 'Evaluado' para estado evaluado", () => {
    render(<InitiativeStatusBadge status="evaluado" />);
    expect(screen.getByText("Evaluado")).toBeInTheDocument();
  });

  it("muestra 'Validado' para estado validado", () => {
    render(<InitiativeStatusBadge status="validado" />);
    expect(screen.getByText("Validado")).toBeInTheDocument();
  });

  it("muestra 'Veredicto' para estado veredicto", () => {
    render(<InitiativeStatusBadge status="veredicto" />);
    expect(screen.getByText("Veredicto")).toBeInTheDocument();
  });

  it("usa color verde para veredicto", () => {
    render(<InitiativeStatusBadge status="veredicto" />);
    const badge = screen.getByText("Veredicto");
    expect(badge.className).toContain("bg-green-100");
    expect(badge.className).toContain("text-green-700");
  });

  it("usa color naranja para en_evaluacion", () => {
    render(<InitiativeStatusBadge status="en_evaluacion" />);
    const badge = screen.getByText("En Evaluación");
    expect(badge.className).toContain("bg-orange-100");
  });

  it("usa color gris para dbi_generado", () => {
    render(<InitiativeStatusBadge status="dbi_generado" />);
    const badge = screen.getByText("DBI Generado");
    expect(badge.className).toContain("bg-gray-100");
  });

  it("usa fallback para estado desconocido", () => {
    render(<InitiativeStatusBadge status={"unknown" as InitiativeStatus} />);
    // Debe usar el config default (dbi_generado)
    expect(screen.getByText("DBI Generado")).toBeInTheDocument();
  });
});
