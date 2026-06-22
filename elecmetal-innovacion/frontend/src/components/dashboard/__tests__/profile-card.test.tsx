import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import ProfileCard from "../profile-card";
import { renderWithProviders } from "@/test/test-utils";

describe("ProfileCard", () => {
  it("muestra el nombre y rol correctamente", () => {
    renderWithProviders(<ProfileCard fullName="Camila Gómez" role="postulante" />);

    expect(screen.getByText(/Camila Gómez/)).toBeInTheDocument();
    expect(screen.getByText(/Rol:/)).toBeInTheDocument();
    expect(screen.getByText(/Postulante/)).toBeInTheDocument();
  });

  it("muestra 'Directora' cuando el rol es directora", () => {
    renderWithProviders(<ProfileCard fullName="Ana Pérez" role="directora" />);

    expect(screen.getByText(/Ana Pérez/)).toBeInTheDocument();
    expect(screen.getByText(/Directora/)).toBeInTheDocument();
  });

  it("muestra rol tal cual si no es conocido", () => {
    renderWithProviders(<ProfileCard fullName="Usuario" role="otro_rol" />);

    expect(screen.getByText(/otro_rol/)).toBeInTheDocument();
  });
});
