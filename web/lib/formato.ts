import { ApiError } from "@/lib/api";

/**
 * Mensaje de error legible para mostrar al usuario: el detalle de la API si
 * lo hay, o un mensaje genérico de conexión.
 */
export function mensajeError(err: unknown): string {
  return err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor";
}

/**
 * Formatea un número como moneda en pesos argentinos (es-AR).
 * Sin decimales si el valor es entero; con hasta 2 decimales si no lo es.
 */
export function moneda(v: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: Number.isInteger(v) ? 0 : 2,
  }).format(v);
}

/**
 * Componentes del índice compuesto, en el orden de la fórmula, con su etiqueta en español.
 */
export const COMPONENTES_INDICE: { clave: string; etiqueta: string }[] = [
  { clave: "documentacion", etiqueta: "Documentación" },
  { clave: "conciliacion", etiqueta: "Conciliación de pagos" },
  { clave: "trazabilidad", etiqueta: "Trazabilidad" },
  { clave: "consistencia", etiqueta: "Consistencia" },
  { clave: "explicaciones", etiqueta: "Explicaciones" },
];

/**
 * Formatea los puntos de un componente del índice: un decimal, coma decimal (es-AR).
 */
export function puntosIndice(v: number): string {
  return v.toLocaleString("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

/**
 * La cuenta de la penalización del índice, tal como se calcula:
 * "36 críticos × 2 = 72 → tope 25", o "sin penalización" cuando no hay críticos abiertos.
 */
export function cuentaPenalizacion(p: { criticos_abiertos: number; por_critico: number; tope: number }): string {
  if (p.criticos_abiertos === 0) return "sin penalización";
  const base = p.criticos_abiertos * p.por_critico;
  const criticos = p.criticos_abiertos === 1 ? "crítico" : "críticos";
  const cuenta = `${p.criticos_abiertos} ${criticos} × ${p.por_critico} = ${base}`;
  return base > p.tope ? `${cuenta} → tope ${p.tope}` : cuenta;
}

/**
 * Formatea una fecha ISO como DD/MM/AAAA HH:mm en horario de Argentina.
 */
export function fecha(iso: string): string {
  const d = new Date(iso);
  const partes = new Intl.DateTimeFormat("es-AR", {
    timeZone: "America/Argentina/Buenos_Aires",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(d);

  const obtener = (tipo: Intl.DateTimeFormatPartTypes) =>
    partes.find((p) => p.type === tipo)?.value ?? "";

  return `${obtener("day")}/${obtener("month")}/${obtener("year")} ${obtener("hour")}:${obtener("minute")}`;
}
