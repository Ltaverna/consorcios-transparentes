import { render, screen } from "@testing-library/react";
import { Sidebar } from "@/components/sidebar";

test("la sidebar muestra las secciones y el contador de pendientes", () => {
  render(<Sidebar rol="auditor" nombre="Lucas" pendientes={10} activa="/panel/hallazgos" />);
  expect(screen.getByText("Hallazgos")).toBeInTheDocument();
  expect(screen.getByText("10")).toBeInTheDocument();
  expect(screen.getByText("Análisis")).toBeInTheDocument();
  expect(screen.getByText("Liquidaciones")).toBeInTheDocument();
  expect(screen.getByText("Consorcio")).toBeInTheDocument();
  expect(screen.getByText(/Asamblea/)).toBeInTheDocument();
  expect(screen.getByText(/Lucas/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Salir" })).toBeInTheDocument();
});
