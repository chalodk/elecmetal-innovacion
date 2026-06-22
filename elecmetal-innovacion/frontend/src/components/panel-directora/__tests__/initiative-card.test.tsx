import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import InitiativeCard from "../initiative-card";
import type { Initiative } from "@/lib/types";

const mockInitiative: Initiative = {
  id: 101,
  session_id: 1,
  user_id: "test-user-id",
  status: "notificado",
  initiative_code: "INI-2026-001",
  title: "Optimización de ciclo de molienda SAG",
  initiative_type: "interna",
  postulation_date: "2026-06-15",
  area: "Mantención Planta",
  applicant_name: "Carlos Muñoz",
  created_at: "2026-06-15T14:30:00-04:00",
  updated_at: "2026-06-15T14:30:00-04:00",
};

describe("InitiativeCard", () => {
  it("muestra el código de la iniciativa", () => {
    render(<InitiativeCard initiative={mockInitiative} onClick={() => {}} />);
    expect(screen.getByText("INI-2026-001")).toBeInTheDocument();
  });

  it("muestra el título", () => {
    render(<InitiativeCard initiative={mockInitiative} onClick={() => {}} />);
    expect(
      screen.getByText("Optimización de ciclo de molienda SAG"),
    ).toBeInTheDocument();
  });

  it("muestra el tipo de iniciativa en español", () => {
    render(<InitiativeCard initiative={mockInitiative} onClick={() => {}} />);
    expect(screen.getByText("Interna")).toBeInTheDocument();
  });

  it("muestra el nombre del postulante y área", () => {
    render(<InitiativeCard initiative={mockInitiative} onClick={() => {}} />);
    expect(screen.getByText(/Carlos Muñoz/)).toBeInTheDocument();
    expect(screen.getByText(/Mantención Planta/)).toBeInTheDocument();
  });

  it("muestra el status badge", () => {
    render(<InitiativeCard initiative={mockInitiative} onClick={() => {}} />);
    expect(screen.getByText("Notificado")).toBeInTheDocument();
  });

  it("llama a onClick con el id al hacer clic", () => {
    const onClick = vi.fn();
    render(<InitiativeCard initiative={mockInitiative} onClick={onClick} />);

    fireEvent.click(screen.getByRole("button"));

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(101);
  });

  it("muestra 'Mixta' para tipo mixta", () => {
    render(
      <InitiativeCard
        initiative={{ ...mockInitiative, initiative_type: "mixta" }}
        onClick={() => {}}
      />,
    );
    expect(screen.getByText("Mixta")).toBeInTheDocument();
  });

  it("muestra 'Externa' para tipo externa", () => {
    render(
      <InitiativeCard
        initiative={{ ...mockInitiative, initiative_type: "externa" }}
        onClick={() => {}}
      />,
    );
    expect(screen.getByText("Externa")).toBeInTheDocument();
  });
});
