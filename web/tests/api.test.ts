// @vitest-environment node
// Entorno node puro (no jsdom): las pruebas de FormData/File del upload necesitan las
// clases nativas de Node/undici para que MSW pueda parsear el cuerpo multipart al
// interceptar el fetch; jsdom trae su propia clase File/FormData, incompatible con eso.
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { api, ApiError, urlInforme, urlContenidoDocumento } from "@/lib/api";

test("un GET devuelve el JSON tipado", async () => {
  servidor.use(http.get(`${API}/liquidaciones`, () =>
    HttpResponse.json([{ id: 1, periodo: "2026-08", estado: "procesada", cuadra: true, sistema: "redconar", error: "" }])));
  const liqs = await api.listarLiquidaciones();
  expect(liqs[0].periodo).toBe("2026-08");
});

test("un error de la API se convierte en ApiError con el detail", async () => {
  servidor.use(http.post(`${API}/auth/login`, () =>
    HttpResponse.json({ detail: "Email o clave incorrectos" }, { status: 401 })));
  await expect(api.login("a@b.com", "mala")).rejects.toMatchObject({ status: 401, detail: "Email o clave incorrectos" });
});

test("subir liquidación manda FormData con archivo y periodo", async () => {
  let form: FormData | null = null;
  servidor.use(http.post(`${API}/liquidaciones`, async ({ request }) => {
    form = await request.formData();
    return HttpResponse.json({ id: 1, periodo: "2026-08", estado: "procesando" });
  }));
  const archivo = new File([new Blob(["x"])], "agosto.pdf");
  await api.subirLiquidacion(archivo, "2026-08");
  expect(form!.get("periodo")).toBe("2026-08");
  expect((form!.get("archivo") as File).name).toBe("agosto.pdf");
});

test("las URLs de archivos apuntan a la API", () => {
  expect(urlInforme("2026-08", "html")).toBe(`${API}/informes/2026-08/html`);
  expect(urlContenidoDocumento(7)).toBe(`${API}/documentos/7/contenido`);
});
