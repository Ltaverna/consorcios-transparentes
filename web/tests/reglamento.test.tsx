import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaReglamento from "@/app/reglamento/page";

test("renderiza la transcripción y el botón del PDF", async () => {
  servidor.use(
    http.get(`${API}/consorcio/reglamento`, () => HttpResponse.json({ pdf: true, transcripcion: true })),
    http.get(`${API}/consorcio/reglamento/transcripcion`, () => HttpResponse.text("# Reglamento de Copropiedad\n\nArtículo primero.")),
  );
  render(<PaginaReglamento />);
  expect(await screen.findByText("Reglamento de Copropiedad")).toBeInTheDocument();
  expect(screen.getByText(/Artículo primero/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Descargar el PDF/ })).toBeInTheDocument();
});

test("sin reglamento cargado muestra el estado vacío", async () => {
  servidor.use(http.get(`${API}/consorcio/reglamento`, () => HttpResponse.json({ pdf: false, transcripcion: false })));
  render(<PaginaReglamento />);
  expect(await screen.findByText(/todavía no está cargado/)).toBeInTheDocument();
});
