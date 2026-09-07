import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaMiUnidad from "@/app/mi-unidad/page";

// Handler de /analitica/indice con 500 → la card se oculta en silencio, el resto de la página sigue funcionando.
const handlerIndice500 = http.get(`${API}/analitica/indice`, () =>
  HttpResponse.json({ detail: "no data" }, { status: 500 }));

// Fixture mínimo de transparencia reutilizado en el test de la card.
const INDICE_MINIMO = {
  indice: 62,
  rango: { desde: "2026-08", hasta: "2026-08" },
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
  periodos: [{
    periodo: "2026-08", indice: 62, pct_trazable: 0.62, pct_con_factura: 0.81, pct_pago_respaldado: 0.7,
    dinero_total: 1000, dinero_verificado: 620, dinero_con_factura: 810, dinero_pago_respaldado: 700,
    gastos_por_estado: {
      verificado: { cantidad: 10, importe: 620 }, requiere_explicacion: { cantidad: 3, importe: 100 },
      anomalia: { cantidad: 2, importe: 150 }, inconsistencia: { cantidad: 1, importe: 80 },
      sin_informacion: { cantidad: 1, importe: 50 },
    },
    hallazgos_abiertos: { "CRÍTICO": 1, ALTO: 2, MEDIO: 3, BAJO: 0 }, hallazgos_resueltos: 4,
  }],
};

test("muestra el informe publicado, la descarga y el estado de cuenta", async () => {
  servidor.use(
    http.get(`${API}/mi-unidad`, () => HttpResponse.json({
      uf: 27, periodo: "2026-08",
      estado_cuenta: { uf: 27, piso_depto: "13-B", propietario: "X", total_mes: 120000, a_pagar: 125000, deuda: 5000 },
      informes: ["/informes/2026-08/html", "/informes/2026-08/xlsx"],
    })),
    http.get(`${API}/hallazgos`, () => HttpResponse.json([])),
    handlerIndice500,
  );
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/13-B/)).toBeInTheDocument();
  expect(screen.getByText(/2026-08/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Descargar Excel/ })).toHaveAttribute("href", expect.stringContaining("/informes/2026-08/xlsx"));
  expect(document.querySelector("iframe")!.getAttribute("src")).toContain("/informes/2026-08/html");
});

test("sin informe publicado muestra un mensaje amable", async () => {
  servidor.use(
    http.get(`${API}/mi-unidad`, () =>
      HttpResponse.json({ detail: "Todavía no hay ningún informe publicado" }, { status: 404 })),
    http.get(`${API}/hallazgos`, () => HttpResponse.json([])),
    handlerIndice500,
  );
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/Todavía no hay ningún informe publicado/)).toBeInTheDocument();
});

test("muestra los hallazgos publicados con sus comprobantes", async () => {
  servidor.use(
    http.get(`${API}/mi-unidad`, () => HttpResponse.json({
      uf: 27, periodo: "2026-08",
      estado_cuenta: { uf: 27, piso_depto: "13-B", propietario: "X", total_mes: 120000, a_pagar: 125000, deuda: 5000 },
      informes: ["/informes/2026-08/html", "/informes/2026-08/xlsx"],
    })),
    http.get(`${API}/hallazgos`, () => HttpResponse.json([
      { id: 61, liquidacion_id: 2, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
        severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pago a un tercero distinto del proveedor",
        monto: 2552000, estado: "pendiente", publicado: true },
    ])),
    http.get(`${API}/hallazgos/61`, () => HttpResponse.json({
      id: 61, liquidacion_id: 2, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
      severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pago a un tercero distinto del proveedor",
      monto: 2552000, estado: "pendiente", publicado: true, refs: ["32"],
      evidencia: "El pago fue a otro CUIT", recomendacion: "Pedir explicación", respuesta_admin: "",
    })),
    http.get(`${API}/documentos`, () => HttpResponse.json([
      { id: 400, gasto_n: 32, tipo: "pago", hash: "x", metadatos: {} },
    ])),
    handlerIndice500,
  );
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/Pago a un tercero/)).toBeInTheDocument();
  expect(screen.getByText(/El pago fue a otro CUIT/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /pago/i })).toHaveAttribute("href", expect.stringContaining("/documentos/400/contenido"));
  expect(document.querySelector("iframe[src*='vista=1']")).toBeTruthy();
});

test("muestra la card de transparencia con el índice y métricas cuando hay períodos publicados", async () => {
  servidor.use(
    http.get(`${API}/mi-unidad`, () => HttpResponse.json({
      uf: 27, periodo: "2026-08",
      estado_cuenta: { uf: 27, piso_depto: "13-B", propietario: "X", total_mes: 120000, a_pagar: 125000, deuda: 5000 },
      informes: ["/informes/2026-08/html", "/informes/2026-08/xlsx"],
    })),
    http.get(`${API}/hallazgos`, () => HttpResponse.json([])),
    http.get(`${API}/analitica/indice`, () => HttpResponse.json(INDICE_MINIMO)),
  );
  render(<PaginaMiUnidad />);
  // La card debe mostrarse con el título, el índice y al menos una etiqueta de métrica.
  expect(await screen.findByText(/Transparencia/)).toBeInTheDocument();
  // El índice grande aparece como "62" seguido de "/ 100"; usamos getAllByText y verificamos que alguno esté en el DOM.
  expect((await screen.findAllByText(/62/)).length).toBeGreaterThan(0);
  expect(screen.getByText(/trazable/i)).toBeInTheDocument();
  // Desglose compacto del índice compuesto: al menos una etiqueta de componente y la penalización.
  expect(screen.getByText(/Documentación/)).toBeInTheDocument();
  expect(screen.getByText(/36 críticos × 2 = 72 → tope 25/)).toBeInTheDocument();
});
