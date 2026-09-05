import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { RolProvider } from "@/components/rol-context";
import ConsorcioPage from "@/app/panel/consorcio/page";
import { FormularioUmbrales } from "@/components/consorcio/umbrales";
import { TablaUnidades } from "@/components/consorcio/unidades";

test("el formulario de umbrales manda el dict completo (semántica PUT)", async () => {
  let cuerpo: any = null;
  servidor.use(http.put(`${API}/consorcio`, async ({ request }) => {
    cuerpo = await request.json();
    return HttpResponse.json({ ok: true });
  }));
  render(<FormularioUmbrales
    umbrales={{ efectivo_linea_alta: 300000 }}
    defaults={{ efectivo_linea_alta: 300000, dias_factura_pago_max: 60 }}
    alGuardar={() => {}} />);
  const campo = screen.getByLabelText("efectivo_linea_alta");
  await userEvent.clear(campo);
  await userEvent.type(campo, "500000");
  await userEvent.click(screen.getByRole("button", { name: "Guardar umbrales" }));
  await waitFor(() => expect(cuerpo).not.toBeNull());
  expect(cuerpo.umbrales.efectivo_linea_alta).toBe(500000);
  expect(cuerpo.umbrales.dias_factura_pago_max).toBe(60); // completa con los defaults
});

test("generar un código lo muestra una sola vez con botón copiar", async () => {
  servidor.use(http.post(`${API}/unidades/27/codigo`, () =>
    HttpResponse.json({ uf: 27, codigo: "abc23456" })));
  render(<TablaUnidades unidades={[{ uf: 27, piso_depto: "13-B", tipo: "", propietario: "X", tiene_codigo: false }] as any} alCambiar={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Generar código/ }));
  expect(await screen.findByText("abc23456")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copiar/ })).toBeInTheDocument();
  expect(screen.getByText(/no se vuelve a mostrar/i)).toBeInTheDocument();
});

test("consejo ve las unidades sin editar datos ni generar códigos", async () => {
  servidor.use(
    http.get(`${API}/consorcio`, () =>
      HttpResponse.json({
        nombre: "Rivadavia 2069", direccion: "", cuit: "", admin_nombre: "", admin_cuit: "", marca: "",
        umbrales: { efectivo_linea_alta: 300000 },
        umbrales_default: { efectivo_linea_alta: 300000 },
      })),
    http.get(`${API}/unidades`, () =>
      HttpResponse.json([
        { uf: 27, piso_depto: "13-B", tipo: "", propietario: "X", tiene_codigo: false },
        { uf: 28, piso_depto: "13-C", tipo: "", propietario: "Y", tiene_codigo: true },
      ])),
  );
  render(
    <RolProvider rol="consejo">
      <ConsorcioPage />
    </RolProvider>
  );
  expect(await screen.findByText("Unidades")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Generar código/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Regenerar/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Guardar/ })).not.toBeInTheDocument();
  expect(screen.queryByText(/Reglamento/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Normativa/)).not.toBeInTheDocument();
});

test("el auditor ve la sección de subida del reglamento con su estado", async () => {
  servidor.use(
    http.get(`${API}/consorcio`, () =>
      HttpResponse.json({
        nombre: "Rivadavia 2069", direccion: "", cuit: "", admin_nombre: "", admin_cuit: "", marca: "",
        umbrales: { efectivo_linea_alta: 300000 },
        umbrales_default: { efectivo_linea_alta: 300000 },
      })),
    http.get(`${API}/unidades`, () => HttpResponse.json([])),
    http.get(`${API}/consorcio/reglamento`, () =>
      HttpResponse.json({ pdf: true, transcripcion: false })),
    http.get(`${API}/consorcio/normativa`, () =>
      HttpResponse.json({ "escala-suterh": false, "acuerdo-paritario": false, "referencia-honorarios": false })),
  );
  render(<ConsorcioPage />); // sin provider: el rol default es auditor
  expect(await screen.findByText("Reglamento")).toBeInTheDocument();
  expect(await screen.findByText(/Normativa de referencia/)).toBeInTheDocument();
  expect(await screen.findByLabelText(/PDF escaneado/)).toBeInTheDocument();
  expect(screen.getByLabelText(/Transcripción/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Subir reglamento" })).toBeInTheDocument();
  // el estado actual: el PDF ya está, la transcripción falta
  expect(await screen.findByText(/PDF: cargado · Transcripción: falta/)).toBeInTheDocument();
});
