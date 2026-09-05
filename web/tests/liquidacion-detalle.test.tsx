import { render, screen } from "@testing-library/react";
import { DetalleLiquidacion } from "@/components/liquidaciones/detalle";

const DETALLE = {
  id: 1, periodo: "2026-08", estado: "procesada", cuadra: true, sistema: "redconar", error: "",
  checks_ok: 30, checks_mal: 0, checks: [],
  totales_categoria: { "Sueldos": 5000000, "Abonos": 1200000 },
  gastos: [
    { n: 1, categoria: "Sueldos", proveedor: "Encargado", concepto: "Sueldo agosto", columna: "A",
      importe: 900000, factura_nro: null, pagos: [{ fecha: "2026-08-05", importe: 900000, caja: "BANCO", forma: "Transferencia" }] },
  ],
};

const DOCS = [{ id: 4, gasto_n: 1, tipo: "pago", hash: "abc", metadatos: {} }];

test("muestra el cuadre en verde y los totales", () => {
  render(<DetalleLiquidacion detalle={DETALLE as any} documentos={DOCS as any} />);
  expect(screen.getByText("30/30")).toBeInTheDocument();
  expect(screen.getAllByText("Sueldos").length).toBeGreaterThanOrEqual(1);
});

test("cada gasto con documentos linkea su comprobante", () => {
  render(<DetalleLiquidacion detalle={DETALLE as any} documentos={DOCS as any} />);
  const link = screen.getByRole("link", { name: /comprobante/i });
  expect(link).toHaveAttribute("href", expect.stringContaining("/documentos/4/contenido"));
});

test("una liquidación que no cuadra muestra los checks fallidos", () => {
  const roto = { ...DETALLE, estado: "no_cuadra", cuadra: false, checks_ok: 28, checks_mal: 2,
    checks: [{ nombre: "total de gastos", ok: false, esperado: 100, obtenido: 90, detalle: "" }] };
  render(<DetalleLiquidacion detalle={roto as any} documentos={[]} />);
  expect(screen.getByText(/total de gastos/)).toBeInTheDocument();
  expect(screen.getByText(/no cuadra/i)).toBeInTheDocument();
});
