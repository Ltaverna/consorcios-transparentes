import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    componentes: {
      documentacion: { peso: 0.3, valor: 0.64, puntos: 19.2 },
      conciliacion: { peso: 0.3, valor: 0.54, puntos: 16.2 },
      trazabilidad: { peso: 0.2, valor: 0.1, puntos: 2.0 },
      consistencia: { peso: 0.1, valor: 0.8, puntos: 8.0, periodos_cuadran: 8, periodos_totales: 10 },
      explicaciones: { peso: 0.1, valor: 0.0, puntos: 0.0 },
    },
    penalizacion: { criticos_abiertos: 36, por_critico: 2, tope: 25, puntos: 25 },
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
  expect(await screen.findByText(/ROTH/)).toBeInTheDocument();
  expect(screen.getByText(/transferencia sin respaldo/)).toBeInTheDocument();

  // Desglose del índice compuesto: tabla de componentes con etiquetas en español.
  expect(screen.getByText("Documentación")).toBeInTheDocument();
  expect(screen.getByText("Conciliación de pagos")).toBeInTheDocument();
  expect(screen.getByText("Trazabilidad")).toBeInTheDocument();
  expect(screen.getByText(/8 de 10 períodos cuadran/)).toBeInTheDocument();
  expect(screen.getByText("Explicaciones")).toBeInTheDocument();
  // Peso 0.30 → "30 %" (documentación y conciliación lo comparten) y puntos "19,2".
  expect(screen.getAllByText("30 %").length).toBeGreaterThan(0);
  expect(screen.getByText("19,2")).toBeInTheDocument();
  // La penalización muestra la cuenta completa: 36 críticos × 2 = 72 → tope 25.
  expect(screen.getByText(/36 críticos × 2 = 72 → tope 25/)).toBeInTheDocument();
  // Cierra con la fórmula del compuesto.
  expect(screen.getByText(/suma de puntos − penalización/)).toBeInTheDocument();
});

test("las filas de estado se operan con teclado y la activa muestra 'filtrando'", async () => {
  const estadosPedidos: (string | null)[] = [];
  servidor.use(
    http.get(`${API}/analitica/indice`, () => HttpResponse.json(INDICE)),
    http.get(`${API}/analitica/gastos`, ({ request }) => {
      estadosPedidos.push(new URL(request.url).searchParams.get("estado"));
      return HttpResponse.json(GASTOS);
    }),
  );
  render(<PaginaTransparencia />);
  await screen.findByText(/ROTH/);

  // la fila es accesible: role="button", enfocable y con Enter aplica el filtro
  const fila = screen.getByRole("button", { name: /Anomalía/ });
  expect(fila).toHaveAttribute("tabindex", "0");
  expect(fila).toHaveAttribute("aria-pressed", "false");
  fila.focus();
  await userEvent.keyboard("{Enter}");
  await waitFor(() => expect(estadosPedidos).toContain("anomalia"));
  expect(fila).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("filtrando")).toBeInTheDocument();

  // Espacio en la fila activa saca el filtro
  await userEvent.keyboard(" ");
  await waitFor(() => expect(fila).toHaveAttribute("aria-pressed", "false"));
  expect(screen.queryByText("filtrando")).not.toBeInTheDocument();
});
