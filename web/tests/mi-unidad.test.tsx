import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaMiUnidad from "@/app/mi-unidad/page";

test("muestra el informe publicado, la descarga y el estado de cuenta", async () => {
  servidor.use(http.get(`${API}/mi-unidad`, () => HttpResponse.json({
    uf: 27, periodo: "2026-08",
    estado_cuenta: { uf: 27, piso_depto: "13-B", propietario: "X", total_mes: 120000, a_pagar: 125000, deuda: 5000 },
    informes: ["/informes/2026-08/html", "/informes/2026-08/xlsx"],
  })));
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/13-B/)).toBeInTheDocument();
  expect(screen.getByText(/2026-08/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Descargar Excel/ })).toHaveAttribute("href", expect.stringContaining("/informes/2026-08/xlsx"));
  expect(document.querySelector("iframe")!.getAttribute("src")).toContain("/informes/2026-08/html");
});

test("sin informe publicado muestra un mensaje amable", async () => {
  servidor.use(http.get(`${API}/mi-unidad`, () =>
    HttpResponse.json({ detail: "Todavía no hay ningún informe publicado" }, { status: 404 })));
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/Todavía no hay ningún informe publicado/)).toBeInTheDocument();
});
