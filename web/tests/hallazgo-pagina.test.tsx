import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaHallazgo from "@/app/panel/hallazgos/[id]/page";
import { RolProvider } from "@/components/rol-context";

// La página usa router.refresh() tras el triage (badge de pendientes de la sidebar).
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }),
}));

const DETALLE = { id: 1, liquidacion_id: 1, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
  severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pagos a la propietaria de 13-B", monto: 4700000,
  estado: "pendiente", publicado: false, evidencia: "CUIT destino ≠ CUIT emisor", recomendacion: "Pedir explicación",
  refs: ["2"], respuesta_admin: "",
  eventos: [{ de: "pendiente", a: "preguntado", nota: "en asamblea", ts: "2026-09-04T10:00:00+00:00", usuario: "Lucas" }] };

test("la página carga el hallazgo con evidencia e historial", async () => {
  servidor.use(
    http.get(`${API}/hallazgos/1`, () => HttpResponse.json(DETALLE)),
    http.get(`${API}/documentos`, () => HttpResponse.json([
      { id: 4, gasto_n: 2, tipo: "factura", hash: "a", metadatos: {} },
      { id: 5, gasto_n: 2, tipo: "pago", hash: "b", metadatos: {} },
    ])),
  );
  render(<PaginaHallazgo params={Promise.resolve({ id: "1" })} />);
  expect(await screen.findAllByText(/Pagos a la propietaria/)).not.toHaveLength(0);
  expect(screen.getByText(/CUIT destino/)).toBeInTheDocument();
  expect(screen.getByText(/en asamblea/)).toBeInTheDocument();
  // visor bajo demanda: un botón por documento (factura y pago del gasto 2) y ningún iframe hasta abrirlo
  expect(document.querySelectorAll("iframe").length).toBe(0);
  expect(screen.getByRole("button", { name: /Ver comprobante: factura/ })).toBeInTheDocument();
  // cada documento también se puede abrir en una pestaña propia
  expect(screen.getAllByRole("link", { name: /pestaña nueva/i }).length).toBe(2);
  await userEvent.click(screen.getByRole("button", { name: /Ver comprobante: pago/ }));
  const visor = await screen.findByTitle("Documento pago");
  expect(visor.getAttribute("src")).toContain("/documentos/5/contenido");
  expect(visor.getAttribute("src")).toContain("vista=1");
});

test("consejo ve el hallazgo sin controles de auditor", async () => {
  servidor.use(
    http.get(`${API}/hallazgos/1`, () => HttpResponse.json({ ...DETALLE, respuesta_admin: "Ya respondimos" })),
    http.get(`${API}/documentos`, () => HttpResponse.json([])),
  );
  render(
    <RolProvider rol="consejo">
      <PaginaHallazgo params={Promise.resolve({ id: "1" })} />
    </RolProvider>
  );
  await screen.findAllByText(/Pagos a la propietaria/);
  expect(screen.queryByLabelText("Publicar en el informe")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /pendiente/i })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Guardar respuesta/ })).not.toBeInTheDocument();
  // la respuesta ya registrada sigue visible como texto
  expect(screen.getByText("Ya respondimos")).toBeInTheDocument();
});

test("un 404 muestra un error visible con reintentar", async () => {
  servidor.use(
    http.get(`${API}/hallazgos/9`, () =>
      HttpResponse.json({ detail: "No existe ese hallazgo" }, { status: 404 })),
    http.get(`${API}/documentos`, () => HttpResponse.json([])));
  render(<PaginaHallazgo params={Promise.resolve({ id: "9" })} />);
  expect(await screen.findByText("No existe ese hallazgo")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Reintentar/ })).toBeInTheDocument();
});
