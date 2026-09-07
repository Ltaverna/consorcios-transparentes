import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { ListaHallazgos } from "@/components/hallazgos/lista";
import { FichaHallazgo } from "@/components/hallazgos/ficha";
import HallazgosPage from "@/app/panel/hallazgos/page";

const navegacion = vi.hoisted(() => ({
  params: new URLSearchParams(),
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navegacion.replace, push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/panel/hallazgos",
  useSearchParams: () => navegacion.params,
}));

beforeEach(() => {
  navegacion.params = new URLSearchParams();
  navegacion.replace.mockClear();
});

const RESUMEN = [
  { id: 1, liquidacion_id: 1, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
    severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pagos a la propietaria de 13-B", monto: 4700000,
    estado: "pendiente", publicado: false },
  { id: 2, liquidacion_id: 1, periodo: "2026-08", regla: "efectivo", origen: "liquidacion",
    severidad: "ALTO", area: "Caja", titulo: "68 % de la liquidez en efectivo", monto: 6700000,
    estado: "preguntado", publicado: true },
];

const DETALLE = { ...RESUMEN[0], evidencia: "CUIT destino ≠ CUIT emisor", recomendacion: "Pedir explicación",
  refs: ["2"], respuesta_admin: "", eventos: [{ de: "", a: "pendiente", nota: "", ts: "2026-09-04T10:00:00+00:00", usuario: "Lucas" }] };

// Filas para las pruebas de la página: desordenadas a propósito para probar el orden.
const PAGINA = [
  { id: 1, liquidacion_id: 1, periodo: "2026-08", regla: "efectivo", origen: "liquidacion",
    severidad: "ALTO", area: "Caja", titulo: "68 % de la liquidez en efectivo", monto: 6700000,
    estado: "preguntado", publicado: true },
  { id: 2, liquidacion_id: 1, periodo: "2026-07", regla: "cae", origen: "comprobantes",
    severidad: "CRÍTICO", area: "Comprobantes", titulo: "Factura sin CAE", monto: 120000,
    estado: "pendiente", publicado: false },
  { id: 3, liquidacion_id: 1, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
    severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pagos a la propietaria de 13-B", monto: 4700000,
    estado: "pendiente", publicado: false },
];

function conApi(filas: unknown[] = PAGINA) {
  servidor.use(
    http.get(`${API}/hallazgos`, () => HttpResponse.json(filas)),
    http.get(`${API}/liquidaciones`, () => HttpResponse.json([
      { id: 1, periodo: "2026-08", estado: "procesada", cuadra: true, sistema: "redconar", error: "" },
      { id: 2, periodo: "2026-07", estado: "procesada", cuadra: true, sistema: "redconar", error: "" },
    ])),
  );
}

function antesQue(primero: HTMLElement, despues: HTMLElement) {
  expect(primero.compareDocumentPosition(despues) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
}

test("la lista muestra severidad, título y monto", () => {
  render(<ListaHallazgos filas={RESUMEN as any} alAbrir={() => {}} />);
  expect(screen.getByText("CRÍTICO")).toBeInTheDocument();
  expect(screen.getByText(/Pagos a la propietaria/)).toBeInTheDocument();
  expect(screen.getByText(/4\.700\.000/)).toBeInTheDocument();
});

test("cambiar el estado pide nota y llama a la API", async () => {
  let cuerpo: any = null;
  servidor.use(http.post(`${API}/hallazgos/1/estado`, async ({ request }) => {
    cuerpo = await request.json();
    return HttpResponse.json({ ok: true, estado: "preguntado" });
  }));
  const alCambiar = vi.fn();
  render(<FichaHallazgo detalle={DETALLE as any} documentos={[]} alCambiar={alCambiar} />);
  await userEvent.click(screen.getByRole("button", { name: "preguntado" }));
  await userEvent.type(screen.getByLabelText(/Nota/), "Se preguntó en la asamblea");
  await userEvent.click(screen.getByRole("button", { name: "Confirmar cambio" }));
  expect(cuerpo).toEqual({ estado: "preguntado", nota: "Se preguntó en la asamblea" });
  expect(alCambiar).toHaveBeenCalled();
});

test("el toggle de publicar llama a la API", async () => {
  let cuerpo: any = null;
  servidor.use(http.post(`${API}/hallazgos/1/publicar`, async ({ request }) => {
    cuerpo = await request.json();
    return HttpResponse.json({ ok: true, publicado: true });
  }));
  render(<FichaHallazgo detalle={DETALLE as any} documentos={[]} alCambiar={() => {}} />);
  await userEvent.click(screen.getByRole("switch", { name: /Publicar en el informe/ }));
  expect(cuerpo).toEqual({ publicado: true });
});

test("la respuesta de la administración se registra", async () => {
  let cuerpo: any = null;
  servidor.use(http.post(`${API}/hallazgos/1/respuesta`, async ({ request }) => {
    cuerpo = await request.json();
    return HttpResponse.json({ ok: true });
  }));
  render(<FichaHallazgo detalle={DETALLE as any} documentos={[]} alCambiar={() => {}} />);
  await userEvent.type(screen.getByLabelText(/Respuesta de la administración/), "Dijeron que lo revisan");
  await userEvent.click(screen.getByRole("button", { name: "Guardar respuesta" }));
  expect(cuerpo).toEqual({ texto: "Dijeron que lo revisan" });
});

// ---- página completa: orden, búsqueda, contador, error, lote, URL

test("ordena por severidad y monto por defecto y muestra el contador con el total", async () => {
  conApi();
  render(<HallazgosPage />);
  expect(await screen.findByText(/Pagos a la propietaria/)).toBeInTheDocument();
  expect(screen.getByText(/3 hallazgos/)).toBeInTheDocument();
  expect(screen.getByText(/11\.520\.000/)).toBeInTheDocument();
  // CRÍTICO de monto alto primero, después CRÍTICO menor, después ALTO aunque tenga más monto.
  antesQue(screen.getByText(/Pagos a la propietaria/), screen.getByText(/Factura sin CAE/));
  antesQue(screen.getByText(/Factura sin CAE/), screen.getByText(/68 % de la liquidez/));
});

test("el control de orden permite ordenar por monto", async () => {
  conApi();
  render(<HallazgosPage />);
  await screen.findByText(/Pagos a la propietaria/);
  await userEvent.selectOptions(screen.getByLabelText("Ordenar por"), "monto");
  antesQue(screen.getByText(/68 % de la liquidez/), screen.getByText(/Pagos a la propietaria/));
  antesQue(screen.getByText(/Pagos a la propietaria/), screen.getByText(/Factura sin CAE/));
});

test("la búsqueda filtra en memoria y el contador dice cuánto se muestra", async () => {
  conApi();
  render(<HallazgosPage />);
  await screen.findByText(/Pagos a la propietaria/);
  await userEvent.type(screen.getByRole("searchbox", { name: /Buscar/ }), "efectivo");
  expect(screen.queryByText(/Pagos a la propietaria/)).not.toBeInTheDocument();
  expect(screen.getByText(/68 % de la liquidez/)).toBeInTheDocument();
  expect(screen.getByText(/Mostrando 1 de 3/)).toBeInTheDocument();
});

test("los chips permiten multi-selección y los de regla salen de las filas", async () => {
  conApi();
  render(<HallazgosPage />);
  await screen.findByText(/Pagos a la propietaria/);
  // chips de regla derivados de las filas cargadas
  expect(screen.getByRole("button", { name: "cae" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "CRÍTICO" }));
  expect(screen.queryByText(/68 % de la liquidez/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "ALTO" }));
  expect(screen.getByText(/68 % de la liquidez/)).toBeInTheDocument();
  expect(screen.getByText(/Pagos a la propietaria/)).toBeInTheDocument();
});

test("los filtros se escriben en la URL y se restauran al montar", async () => {
  conApi();
  render(<HallazgosPage />);
  await screen.findByText(/Pagos a la propietaria/);
  await userEvent.click(screen.getByRole("button", { name: "pendiente" }));
  await waitFor(() => {
    const destino = navegacion.replace.mock.lastCall?.[0] as string;
    expect(destino).toContain("estado=pendiente");
  });
});

test("con filtros en la URL la lista arranca filtrada", async () => {
  navegacion.params = new URLSearchParams("estado=preguntado");
  conApi();
  render(<HallazgosPage />);
  expect(await screen.findByText(/68 % de la liquidez/)).toBeInTheDocument();
  expect(screen.queryByText(/Pagos a la propietaria/)).not.toBeInTheDocument();
});

test("si la carga falla hay card de error con Reintentar (no un vacío mentiroso)", async () => {
  servidor.use(
    http.get(`${API}/hallazgos`, () => HttpResponse.json({ detail: "Se cayó la base" }, { status: 500 }), { once: true }),
    http.get(`${API}/hallazgos`, () => HttpResponse.json(PAGINA)),
    http.get(`${API}/liquidaciones`, () => HttpResponse.json([])),
  );
  render(<HallazgosPage />);
  expect(await screen.findByText("Se cayó la base")).toBeInTheDocument();
  expect(screen.queryByText(/No hay hallazgos/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
  expect(await screen.findByText(/Pagos a la propietaria/)).toBeInTheDocument();
});

test("seleccionar tarjetas muestra la barra de lote y dispara los pedidos por id", async () => {
  conApi();
  const cambiados: { id: number; estado: string }[] = [];
  servidor.use(
    http.post(`${API}/hallazgos/:id/estado`, async ({ params, request }) => {
      const cuerpo = (await request.json()) as { estado: string };
      cambiados.push({ id: Number(params.id), estado: cuerpo.estado });
      return HttpResponse.json({ ok: true, estado: cuerpo.estado });
    }),
  );
  render(<HallazgosPage />);
  await screen.findByText(/Pagos a la propietaria/);
  await userEvent.click(screen.getByRole("checkbox", { name: /Seleccionar Pagos a la propietaria/ }));
  await userEvent.click(screen.getByRole("checkbox", { name: /Seleccionar Factura sin CAE/ }));
  expect(screen.getByText("2 seleccionados")).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("Nuevo estado"), "preguntado");
  await userEvent.click(screen.getByRole("button", { name: "Cambiar estado" }));
  expect(screen.getByText(/Cambiar 2 hallazgos a/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  await waitFor(() => {
    expect(cambiados.map((c) => c.id).sort()).toEqual([2, 3]);
  });
  expect(cambiados.every((c) => c.estado === "preguntado")).toBe(true);
});

test("si parte del lote falla, los fallidos quedan seleccionados para reintentar", async () => {
  conApi();
  servidor.use(
    http.post(`${API}/hallazgos/2/estado`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
    http.post(`${API}/hallazgos/3/estado`, () => HttpResponse.json({ ok: true, estado: "preguntado" })),
  );
  render(<HallazgosPage />);
  await screen.findByText(/Pagos a la propietaria/);
  await userEvent.click(screen.getByRole("checkbox", { name: /Seleccionar Pagos a la propietaria/ }));
  await userEvent.click(screen.getByRole("checkbox", { name: /Seleccionar Factura sin CAE/ }));
  await userEvent.click(screen.getByRole("button", { name: "Cambiar estado" }));
  await userEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  expect(await screen.findByText("1 seleccionado")).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: /Seleccionar Factura sin CAE/ })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: /Seleccionar Pagos a la propietaria/ })).not.toBeChecked();
});
