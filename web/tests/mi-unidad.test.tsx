import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaMiUnidad from "@/app/mi-unidad/page";

test("muestra el informe publicado, la descarga y el estado de cuenta", async () => {
  servidor.use(
    http.get(`${API}/mi-unidad`, () => HttpResponse.json({
      uf: 27, periodo: "2026-08",
      estado_cuenta: { uf: 27, piso_depto: "13-B", propietario: "X", total_mes: 120000, a_pagar: 125000, deuda: 5000 },
      informes: ["/informes/2026-08/html", "/informes/2026-08/xlsx"],
    })),
    http.get(`${API}/hallazgos`, () => HttpResponse.json([])),
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
  );
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/Pago a un tercero/)).toBeInTheDocument();
  expect(screen.getByText(/El pago fue a otro CUIT/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /pago/i })).toHaveAttribute("href", expect.stringContaining("/documentos/400/contenido"));
  expect(document.querySelector("iframe[src*='vista=1']")).toBeTruthy();
});
