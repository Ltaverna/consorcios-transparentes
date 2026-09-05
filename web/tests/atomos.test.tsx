import { render, screen } from "@testing-library/react";
import { ChipSeveridad } from "@/components/severidad";
import { ChipEstado } from "@/components/estado-hallazgo";
import { Kpi } from "@/components/kpi";
import { moneda } from "@/lib/formato";

// Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", ... })
// separa el símbolo "$" del monto con un espacio de no separación
// normal (NBSP, U+00A0), no con el espacio fino (NNBSP, U+202F).
// Verificado con: node -e 'console.log(JSON.stringify(new Intl.NumberFormat("es-AR",
//   { style: "currency", currency: "ARS", maximumFractionDigits: 0 }).format(4700000)))'
const NBSP = " ";

test("moneda formatea en pesos argentinos", () => {
  expect(moneda(4700000)).toBe(`$${NBSP}4.700.000`); // Intl es-AR con espacio duro
  expect(moneda(-1500.5)).toContain("1.500,50");
});

test("el chip de severidad usa el color correcto", () => {
  render(<ChipSeveridad severidad="CRÍTICO" />);
  const chip = screen.getByText("CRÍTICO");
  expect(chip).toHaveClass("text-[#B42318]");
});

test("el chip de estado muestra el estado", () => {
  render(<ChipEstado estado="preguntado" />);
  expect(screen.getByText("preguntado")).toBeInTheDocument();
});

test("el KPI muestra etiqueta y valor", () => {
  render(<Kpi etiqueta="Críticos" valor="10" tono="critico" />);
  expect(screen.getByText("Críticos")).toBeInTheDocument();
  expect(screen.getByText("10")).toBeInTheDocument();
});
