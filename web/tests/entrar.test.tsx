import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { FormulariosEntrar } from "@/components/login-forms";

// jsdom no implementa una navegación real: asignar `window.location.href` tira
// "Not implemented: navigation" y hace fallar el test. `lib/api.ts` sólo hace esa
// asignación en un 401 cuando `pathname` NO empieza con "/entrar" (para no generar un
// loop de redirects). Como jsdom arranca en "http://localhost/", ese guard no protege
// acá. En vez de tocar `lib/api.ts`, reemplazamos `window.location` por un stub cuyo
// `pathname` ya es "/entrar": el guard evita la asignación de `href` y no hay throw.
Object.defineProperty(window, "location", {
  value: { ...window.location, pathname: "/entrar", href: "http://localhost/entrar" },
  writable: true,
});

const irA = vi.fn();

test("login de equipo exitoso llama al callback con el rol", async () => {
  servidor.use(http.post(`${API}/auth/login`, () => HttpResponse.json({ rol: "auditor", nombre: "Lucas" })));
  render(<FormulariosEntrar alEntrar={irA} />);
  await userEvent.type(screen.getByLabelText("Email"), "lucas@example.com");
  await userEvent.type(screen.getByLabelText("Clave"), "clave-larga");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(irA).toHaveBeenCalledWith("auditor");
});

test("login incorrecto muestra el mensaje de la API", async () => {
  servidor.use(http.post(`${API}/auth/login`, () =>
    HttpResponse.json({ detail: "Email o clave incorrectos" }, { status: 401 })));
  render(<FormulariosEntrar alEntrar={irA} />);
  await userEvent.type(screen.getByLabelText("Email"), "x@x.com");
  await userEvent.type(screen.getByLabelText("Clave"), "mala-clave");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(await screen.findByText("Email o clave incorrectos")).toBeInTheDocument();
});

test("la pestaña Propietario pide UF y código y entra", async () => {
  servidor.use(http.post(`${API}/auth/login-unidad`, () =>
    HttpResponse.json({ rol: "propietario", uf: 27, piso_depto: "13-B" })));
  render(<FormulariosEntrar alEntrar={irA} />);
  await userEvent.click(screen.getByRole("tab", { name: "Propietario" }));
  await userEvent.type(screen.getByLabelText("Unidad funcional (UF)"), "27");
  await userEvent.type(screen.getByLabelText("Código de acceso"), "abc23456");
  await userEvent.click(screen.getByRole("button", { name: "Entrar a mi unidad" }));
  expect(irA).toHaveBeenCalledWith("propietario");
});

test("con client ID configurado aparece el botón de Google en la pestaña Equipo", () => {
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "cid-test");
  render(<FormulariosEntrar alEntrar={() => {}} />);
  expect(screen.getByTestId("boton-google")).toBeInTheDocument();
  vi.unstubAllEnvs();
});

test("sin client ID no hay botón de Google", () => {
  render(<FormulariosEntrar alEntrar={() => {}} />);
  expect(screen.queryByTestId("boton-google")).not.toBeInTheDocument();
});
