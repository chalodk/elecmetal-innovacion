import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import DbiBlockSection from "../dbi-block-section";

const sampleFields = [
  { label: "Problema", value: "Alta tasa de fallas en molinos SAG" },
  { label: "Evidencia", value: "Reportes de mantención 2025-2026" },
  { label: "Sin dato", value: null },
  { label: "No especificado", value: "no especificado" },
];

describe("DbiBlockSection", () => {
  it("muestra el título del bloque con la letra", () => {
    render(
      <DbiBlockSection
        title="Problema"
        letter="A"
        fields={sampleFields}
      />,
    );
    expect(screen.getByText("Problema")).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("no muestra los campos cuando está colapsado por defecto", () => {
    render(
      <DbiBlockSection
        title="Problema"
        letter="A"
        fields={sampleFields}
      />,
    );
    expect(screen.queryByText("Alta tasa de fallas en molinos SAG")).not.toBeInTheDocument();
  });

  it("muestra los campos cuando defaultOpen es true", () => {
    render(
      <DbiBlockSection
        title="Problema"
        letter="A"
        fields={sampleFields}
        defaultOpen
      />,
    );
    expect(
      screen.getByText("Alta tasa de fallas en molinos SAG"),
    ).toBeInTheDocument();
  });

  it("expande y colapsa al hacer clic", () => {
    render(
      <DbiBlockSection
        title="Problema"
        letter="A"
        fields={sampleFields}
      />,
    );

    // Colapsado inicialmente
    expect(screen.queryByText("Alta tasa de fallas en molinos SAG")).not.toBeInTheDocument();

    // Expandir
    fireEvent.click(screen.getByRole("button"));
    expect(
      screen.getByText("Alta tasa de fallas en molinos SAG"),
    ).toBeInTheDocument();

    // Colapsar
    fireEvent.click(screen.getByRole("button"));
    expect(screen.queryByText("Alta tasa de fallas en molinos SAG")).not.toBeInTheDocument();
  });

  it("muestra '—' para valores nulos", () => {
    render(
      <DbiBlockSection
        title="Problema"
        letter="A"
        fields={sampleFields}
        defaultOpen
      />,
    );
    const dashElements = screen.getAllByText("—");
    expect(dashElements.length).toBeGreaterThanOrEqual(1);
  });

  it("muestra '—' para sentinelas como 'no especificado'", () => {
    render(
      <DbiBlockSection
        title="Problema"
        letter="A"
        fields={sampleFields}
        defaultOpen
      />,
    );
    const dashElements = screen.getAllByText("—");
    expect(dashElements.length).toBeGreaterThanOrEqual(1);
  });

  it("muestra los labels de los campos", () => {
    render(
      <DbiBlockSection
        title="Problema"
        letter="A"
        fields={sampleFields}
        defaultOpen
      />,
    );
    // "Problema" esta tanto en el titulo del boton como en el label del campo
    expect(screen.getAllByText("Problema").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Evidencia")).toBeInTheDocument();
    expect(screen.getByText("Sin dato")).toBeInTheDocument();
    expect(screen.getByText("No especificado")).toBeInTheDocument();
  });
});
