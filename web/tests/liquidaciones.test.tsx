import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { RolProvider } from "@/components/rol-context";
import LiquidacionesPage from "@/app/panel/liquidaciones/page";
import { ListaLiquidaciones } from "@/components/liquidaciones/lista";
import { SubirLiquidacion } from "@/components/liquidaciones/subir-liquidacion";

const FILAS = [
  { id: 1, periodo: "2026-08", estado: "procesada", cuadra: true, sistema: "redconar", error: "" },
  { id: 2, periodo: "2026-07", estado: "no_cuadra", cuadra: false, sistema: "redconar", error: "" },
  { id: 3, periodo: "2026-06", estado: "error", cuadra: false, sistema: "", error: "El documento es de 2026-05, no de 2026-06" },
];

test("la lista muestra período, estado y el error cuando lo hay", () => {
  render(<ListaLiquidaciones filas={FILAS as any} alCambiar={() => {}} />);
  expect(screen.getByText("2026-08")).toBeInTheDocument();
  expect(screen.getByText("procesada")).toBeInTheDocument();
  expect(screen.getByText("no cuadra")).toBeInTheDocument();
  expect(screen.getByText(/El documento es de 2026-05/)).toBeInTheDocument();
});

test("subir una liquidación manda el archivo y avisa el resultado", async () => {
  servidor.use(http.post(`${API}/liquidaciones`, () =>
    HttpResponse.json({ id: 9, periodo: "2026-09", estado: "procesando" })));
  const alSubir = vi.fn();
  render(<SubirLiquidacion alSubir={alSubir} />);
  // el período es un selector de mes precargado con el mes actual (AAAA-MM, lo que espera la API)
  const periodo = screen.getByLabelText("Período") as HTMLInputElement;
  expect(periodo).toHaveAttribute("type", "month");
  const hoy = new Date();
  expect(periodo.value).toBe(`${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, "0")}`);
  fireEvent.change(periodo, { target: { value: "2026-09" } });
  const archivo = new File(["contenido"], "septiembre.pdf", { type: "application/pdf" });
  await userEvent.upload(screen.getByLabelText(/Liquidación en PDF/), archivo);
  await userEvent.click(screen.getByRole("button", { name: "Subir y procesar" }));
  expect(await screen.findByText(/procesando/i)).toBeInTheDocument();
  expect(alSubir).toHaveBeenCalled();
});

test("un 413 de la API se muestra tal cual", async () => {
  servidor.use(http.post(`${API}/liquidaciones`, () =>
    HttpResponse.json({ detail: "El archivo supera los 30 MB" }, { status: 413 })));
  render(<SubirLiquidacion alSubir={() => {}} />);
  fireEvent.change(screen.getByLabelText("Período"), { target: { value: "2026-09" } });
  await userEvent.upload(screen.getByLabelText(/Liquidación en PDF/), new File(["x"], "x.pdf"));
  await userEvent.click(screen.getByRole("button", { name: "Subir y procesar" }));
  expect(await screen.findByText("El archivo supera los 30 MB")).toBeInTheDocument();
});

test("consejo ve la lista sin el formulario de subir ni el de comprobantes", async () => {
  servidor.use(http.get(`${API}/liquidaciones`, () => HttpResponse.json(FILAS)));
  render(
    <RolProvider rol="consejo">
      <LiquidacionesPage />
    </RolProvider>
  );
  expect(await screen.findByText("2026-08")).toBeInTheDocument();
  expect(screen.getByText("Liquidaciones")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Subir y procesar/ })).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/Período/)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /comprobantes/i })).not.toBeInTheDocument();
});
