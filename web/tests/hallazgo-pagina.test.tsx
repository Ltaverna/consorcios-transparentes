import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaHallazgo from "@/app/panel/hallazgos/[id]/page";
import { RolProvider } from "@/components/rol-context";

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
  // visor lado a lado: dos iframes (factura y pago del gasto 2)
  expect(document.querySelectorAll("iframe").length).toBe(2);
  // el visor pide la vista inline; el link de al lado sigue siendo descarga
  const iframes = Array.from(document.querySelectorAll("iframe"));
  expect(iframes.every((f) => f.getAttribute("src")?.endsWith("?vista=1"))).toBe(true);
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
  expect(screen.queryByRole("button", { name: "pendiente" })).not.toBeInTheDocument();
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
