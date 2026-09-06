import { http, HttpResponse } from "msw";
import { render, screen } from "@testing-library/react";
import { servidor, API } from "./msw";
import PaginaTransparencia from "@/app/panel/transparencia/page";

const INDICE = {
  indice: 62,
  rango: { desde: "2026-07", hasta: "2026-08" },
  totales: {
    dinero_total: 1000, dinero_verificado: 620, dinero_con_factura: 810, dinero_pago_respaldado: 700,
    pct_trazable: 0.62, pct_con_factura: 0.81, pct_pago_respaldado: 0.7, indice: 62,
    gastos_por_estado: {
      verificado: { cantidad: 10, importe: 620 }, requiere_explicacion: { cantidad: 3, importe: 100 },
      anomalia: { cantidad: 2, importe: 150 }, inconsistencia: { cantidad: 1, importe: 80 },
      sin_informacion: { cantidad: 1, importe: 50 },
    },
    hallazgos_abiertos: { "CRÍTICO": 1, ALTO: 2, MEDIO: 3, BAJO: 0 }, hallazgos_resueltos: 4,
  },
  periodos: [{ periodo: "2026-08", indice: 62, pct_trazable: 0.62, pct_con_factura: 0.81,
               pct_pago_respaldado: 0.7, dinero_total: 1000, dinero_verificado: 620,
               dinero_con_factura: 810, dinero_pago_respaldado: 700,
               gastos_por_estado: { verificado: { cantidad: 10, importe: 620 }, requiere_explicacion: { cantidad: 3, importe: 100 }, anomalia: { cantidad: 2, importe: 150 }, inconsistencia: { cantidad: 1, importe: 80 }, sin_informacion: { cantidad: 1, importe: 50 } },
               hallazgos_abiertos: { "CRÍTICO": 1, ALTO: 2, MEDIO: 3, BAJO: 0 }, hallazgos_resueltos: 4 }],
};

const GASTOS = { periodo: "2026-08", gastos: [
  { n: 25, proveedor: "MARIO LEONARDO ROTH", categoria: "ABONOS", concepto: "Serpentina",
    importe: 2650000, estado: "anomalia",
    hallazgos: [{ id: 7, severidad: "ALTO", estado: "pendiente", titulo: "transferencia sin respaldo" }],
    documentos: [{ id: 1, tipo: "factura", archivo: "fc.pdf" }] },
] };

test("muestra el índice, las métricas y el drill-down", async () => {
  servidor.use(
    http.get(`${API}/analitica/indice`, () => HttpResponse.json(INDICE)),
    http.get(`${API}/analitica/gastos`, () => HttpResponse.json(GASTOS)),
  );
  render(<PaginaTransparencia />);
  // /^62$/ y no /62/: los importes de las barras y la tabla ($ 620) también contienen "62".
  expect(await screen.findByText(/^62$/)).toBeInTheDocument();
  expect(screen.getByText(/trazable/i)).toBeInTheDocument();
  expect(await screen.findByText(/ROTH/)).toBeInTheDocument();
  expect(screen.getByText(/transferencia sin respaldo/)).toBeInTheDocument();
});
