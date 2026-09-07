import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { FormulariosEntrar } from "@/components/login-forms";
import EntrarPage from "@/app/entrar/page";

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

const navegacion = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navegacion.replace, push: navegacion.push }),
}));

beforeEach(() => {
  navegacion.replace.mockClear();
  navegacion.push.mockClear();
});

const irA = vi.fn();

// ---- FormulariosEntrar: tab por defecto y contenido ----

test("la pestaña Propietario está activa por defecto", () => {
  servidor.use(http.get(`${API}/auth/yo`, () => HttpResponse.json({ detail: "no session" }, { status: 401 })));
  render(<FormulariosEntrar alEntrar={() => {}} />);
  // Con defaultValue="propietario" el formulario de unidad funcional está visible desde el inicio.
  expect(screen.getByLabelText("Unidad funcional (UF)")).toBeInTheDocument();
  // La pestaña Equipo no muestra su formulario sin hacer clic.
  expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
});

test("el texto de ayuda del código de acceso está presente", () => {
  render(<FormulariosEntrar alEntrar={() => {}} />);
  expect(
    screen.getByText(
      /Es el código que te entregó el consejo o el auditor\. Si no lo tenés, pedilo en la administración del consorcio\./
    )
  ).toBeInTheDocument();
});

// ---- FormulariosEntrar: flujos de login ----

test("login de equipo exitoso llama al callback con el rol", async () => {
  servidor.use(http.post(`${API}/auth/login`, () => HttpResponse.json({ rol: "auditor", nombre: "Lucas" })));
  render(<FormulariosEntrar alEntrar={irA} />);
  // Cambiar a la pestaña Equipo antes de completar el formulario.
  await userEvent.click(screen.getByRole("tab", { name: "Equipo" }));
  await userEvent.type(screen.getByLabelText("Email"), "lucas@example.com");
  await userEvent.type(screen.getByLabelText("Clave"), "clave-larga");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(irA).toHaveBeenCalledWith("auditor");
});

test("login incorrecto muestra el mensaje de la API", async () => {
  servidor.use(http.post(`${API}/auth/login`, () =>
    HttpResponse.json({ detail: "Email o clave incorrectos" }, { status: 401 })));
  render(<FormulariosEntrar alEntrar={irA} />);
  await userEvent.click(screen.getByRole("tab", { name: "Equipo" }));
  await userEvent.type(screen.getByLabelText("Email"), "x@x.com");
  await userEvent.type(screen.getByLabelText("Clave"), "mala-clave");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(await screen.findByText("Email o clave incorrectos")).toBeInTheDocument();
});

test("la pestaña Propietario pide UF y código y entra", async () => {
  servidor.use(http.post(`${API}/auth/login-unidad`, () =>
    HttpResponse.json({ rol: "propietario", uf: 27, piso_depto: "13-B" })));
  render(<FormulariosEntrar alEntrar={irA} />);
  // Con defaultValue="propietario" ya estamos en la pestaña correcta — no hace falta hacer clic.
  await userEvent.type(screen.getByLabelText("Unidad funcional (UF)"), "27");
  await userEvent.type(screen.getByLabelText("Código de acceso"), "abc23456");
  await userEvent.click(screen.getByRole("button", { name: "Entrar a mi unidad" }));
  expect(irA).toHaveBeenCalledWith("propietario");
});

test("con client ID configurado aparece el botón de Google en la pestaña Equipo", async () => {
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "cid-test");
  render(<FormulariosEntrar alEntrar={() => {}} />);
  await userEvent.click(screen.getByRole("tab", { name: "Equipo" }));
  expect(screen.getByTestId("boton-google")).toBeInTheDocument();
  vi.unstubAllEnvs();
});

test("sin client ID no hay botón de Google", async () => {
  render(<FormulariosEntrar alEntrar={() => {}} />);
  await userEvent.click(screen.getByRole("tab", { name: "Equipo" }));
  expect(screen.queryByTestId("boton-google")).not.toBeInTheDocument();
});

// ---- EntrarPage: comprobación de sesión al montar ----

test("al montar /entrar, si api.yo() falla (sin sesión), el formulario sigue visible", async () => {
  servidor.use(http.get(`${API}/auth/yo`, () =>
    HttpResponse.json({ detail: "no autenticado" }, { status: 401 })));
  render(<EntrarPage />);
  // El formulario está presente inmediatamente (sin bloqueo de render).
  expect(screen.getByRole("tab", { name: "Propietario" })).toBeInTheDocument();
  // Esperamos a que el efecto se resuelva y verificamos que no hubo redirección.
  await waitFor(() => {
    expect(navegacion.replace).not.toHaveBeenCalled();
  });
});

test("al montar /entrar, si api.yo() tiene éxito (propietario), redirige a /mi-unidad", async () => {
  servidor.use(http.get(`${API}/auth/yo`, () =>
    HttpResponse.json({ rol: "propietario", uf: 27 })));
  render(<EntrarPage />);
  await waitFor(() => {
    expect(navegacion.replace).toHaveBeenCalledWith("/mi-unidad");
  });
});

test("al montar /entrar, si api.yo() tiene éxito (auditor), redirige a /panel", async () => {
  servidor.use(http.get(`${API}/auth/yo`, () =>
    HttpResponse.json({ rol: "auditor", nombre: "Lucas" })));
  render(<EntrarPage />);
  await waitFor(() => {
    expect(navegacion.replace).toHaveBeenCalledWith("/panel");
  });
});
