import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

/** Fetch server-side contra la API reenviando la cookie de sesión del navegador. */
export async function pedirServidor<T>(path: string): Promise<T> {
  const jar = await cookies();
  const res = await fetch(`${BASE}${path}`, {
    headers: { Cookie: jar.toString() },
    cache: "no-store",
  });
  if (res.status === 401) redirect("/entrar");
  if (!res.ok) throw new Error(`API ${res.status} en ${path}`);
  return res.json() as Promise<T>;
}
