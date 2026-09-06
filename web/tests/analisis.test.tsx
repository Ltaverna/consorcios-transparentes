import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaAnalisis from "@/app/panel/analisis/page";

const GRUPOS = { grupos: [
  { clave: "SACZEWICZYK MARIA EUGENIA", total: 5252000, cantidad: 3, variacion: 0.28 },
  { clave: "EDESUR S A", total: 1721032, cantidad: 3, variacion: -0.06 },
] };
const CATS = { grupos: [{ clave: "SUELDOS", total: 7000000, cantidad: 10, variacion: null }] };

test("renderiza el ranking de proveedores con variación", async () => {
  servidor.use(
    http.get(`${API}/consulta/agregados`, ({ request }) => {
      const por = new URL(request.url).searchParams.get("por");
      return HttpResponse.json(por === "proveedor" ? GRUPOS : CATS);
    }),
  );
  render(<PaginaAnalisis />);
  expect(await screen.findByText(/SACZEWICZYK/)).toBeInTheDocument();
  expect(screen.getByText(/\+28/)).toBeInTheDocument();
  expect(screen.getByText(/SUELDOS/)).toBeInTheDocument();
});

test("el buscador de gastos consulta y muestra resultados", async () => {
  servidor.use(
    http.get(`${API}/consulta/agregados`, () => HttpResponse.json({ grupos: [] })),
    http.get(`${API}/consulta/gastos`, () => HttpResponse.json({
      filas: [{ periodo: "2026-08", n: 32, proveedor: "SACZEWICZYK MARIA EUGENIA",
                categoria: "MANTENIMIENTO", concepto: "Impermeabilización", importe: 2552000,
                factura_nro: "N° 7", pagos: [] }],
      total: 2552000, cantidad: 1,
    })),
  );
  render(<PaginaAnalisis />);
  const { fireEvent } = await import("@testing-library/react");
  fireEvent.change(await screen.findByLabelText(/Proveedor/), { target: { value: "sacze" } });
  fireEvent.click(screen.getByRole("button", { name: /Buscar/ }));
  expect(await screen.findByText(/Impermeabilización/)).toBeInTheDocument();
  expect(screen.getByText(/2\.552\.000/)).toBeInTheDocument();
});
