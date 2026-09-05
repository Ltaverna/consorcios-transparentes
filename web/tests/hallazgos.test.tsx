import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { ListaHallazgos } from "@/components/hallazgos/lista";
import { FichaHallazgo } from "@/components/hallazgos/ficha";

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
