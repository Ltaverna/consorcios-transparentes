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
