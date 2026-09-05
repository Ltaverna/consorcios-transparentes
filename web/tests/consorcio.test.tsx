import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
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
