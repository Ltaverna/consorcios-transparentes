/**
 * Cliente tipado de la API del motor (FastAPI). Centraliza el `fetch` con cookies de
 * sesión, la conversión de errores HTTP a `ApiError` y la redirección a `/entrar`
 * cuando la sesión vence (401).
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function pedir<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, { credentials: "include", ...init });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const cuerpo = await res.json();
      if (cuerpo && typeof cuerpo.detail === "string") detail = cuerpo.detail;
    } catch {
      // el cuerpo no era JSON: nos quedamos con el statusText
    }
    if (res.status === 401 && typeof window !== "undefined" && !window.location.pathname.startsWith("/entrar")) {
      window.location.href = "/entrar";
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

function conJson(method: "POST" | "PUT", cuerpo: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) };
}

// ---- tipos

export type Rol = "auditor" | "consejo" | "moderador" | "propietario";

export interface Yo {
  rol: Rol;
  uf?: number;
  nombre?: string;
}

export interface LiquidacionResumen {
  id: number;
  periodo: string;
  estado: string;
  cuadra: boolean;
  sistema: string;
  error: string;
}

export interface Check {
  nombre: string;
  ok: boolean;
  esperado: unknown;
  obtenido: unknown;
  detalle: string;
}

export interface PagoGasto {
  fecha: string | null;
  importe: number;
  caja: string;
  forma: string;
}

export interface GastoFila {
  n: number;
  categoria: string;
  proveedor: string;
  concepto: string;
  columna: string;
  importe: number;
  factura_nro: string | null;
  pagos: PagoGasto[];
}

export interface LiquidacionDetalle extends LiquidacionResumen {
  checks_ok: number;
  checks_mal: number;
  checks: Check[];
  totales_categoria: Record<string, number>;
  gastos: GastoFila[];
}

export interface HallazgoResumen {
  id: number;
  liquidacion_id: number;
  periodo: string;
  regla: string;
  origen: string;
  severidad: string;
  area: string;
  titulo: string;
  monto: number;
  estado: string;
  publicado: boolean;
}

export interface EventoHallazgo {
  de: string;
  a: string;
  nota: string;
  ts: string;
  usuario: string;
}

export interface HallazgoDetalle extends HallazgoResumen {
  evidencia: unknown;
  recomendacion: string;
  refs: string[];
  respuesta_admin: string;
  eventos: EventoHallazgo[];
}

export interface ConsorcioInfo {
  nombre: string;
  direccion: string;
  cuit: string;
  admin_nombre: string;
  admin_cuit: string;
  marca: string;
  umbrales: Record<string, number>;
  umbrales_default: Record<string, number>;
}

export interface UnidadFila {
  uf: number;
  piso_depto: string;
  tipo: string;
  propietario: string;
  tiene_codigo: boolean;
}

export interface DocumentoInfo {
  id: number;
  gasto_n: number | null;
  tipo: string;
  hash: string;
  metadatos: Record<string, unknown>;
}

export interface EstadoCuenta {
  uf: number;
  piso_depto: string;
  propietario: string;
  total_mes: number;
  a_pagar: number;
  deuda: number;
}

export interface MiUnidad {
  uf: number;
  periodo: string;
  estado_cuenta: EstadoCuenta | null;
  informes: string[];
}

// ---- llamadas

export const api = {
  login(email: string, clave: string) {
    return pedir<{ rol: Rol; nombre: string }>("/auth/login", conJson("POST", { email, clave }));
  },

  loginGoogle(credential: string) {
    return pedir<{ rol: Rol; nombre: string }>("/auth/login-google", conJson("POST", { credential }));
  },

  loginUnidad(uf: number, codigo: string) {
    return pedir<{ rol: Rol; uf: number; piso_depto: string }>("/auth/login-unidad", conJson("POST", { uf, codigo }));
  },

  salir() {
    return pedir<{ ok: boolean }>("/auth/salir", { method: "POST" });
  },

  yo() {
    return pedir<Yo>("/auth/yo");
  },

  listarLiquidaciones() {
    return pedir<LiquidacionResumen[]>("/liquidaciones");
  },

  detalleLiquidacion(id: number) {
    return pedir<LiquidacionDetalle>(`/liquidaciones/${id}`);
  },

  subirLiquidacion(archivo: File, periodo: string) {
    const form = new FormData();
    form.set("archivo", archivo);
    form.set("periodo", periodo);
    return pedir<{ id: number; periodo: string; estado: string }>("/liquidaciones", { method: "POST", body: form });
  },

  subirComprobantes(id: number, archivo: File) {
    const form = new FormData();
    form.set("archivo", archivo);
    return pedir<{ ok: boolean; documentos: number; hallazgos_cruce: number }>(
      `/liquidaciones/${id}/comprobantes`, { method: "POST", body: form });
  },

  publicarLiquidacion(id: number) {
    return pedir<{ ok: boolean; hallazgos_publicados: number }>(`/liquidaciones/${id}/publicar`, { method: "POST" });
  },

  listarHallazgos(filtros?: { severidad?: string; estado?: string; regla?: string; periodo?: string }) {
    const params = new URLSearchParams();
    if (filtros?.severidad) params.set("severidad", filtros.severidad);
    if (filtros?.estado) params.set("estado", filtros.estado);
    if (filtros?.regla) params.set("regla", filtros.regla);
    if (filtros?.periodo) params.set("periodo", filtros.periodo);
    const qs = params.toString();
    return pedir<HallazgoResumen[]>(`/hallazgos${qs ? `?${qs}` : ""}`);
  },

  detalleHallazgo(id: number) {
    return pedir<HallazgoDetalle>(`/hallazgos/${id}`);
  },

  cambiarEstado(id: number, estado: string, nota: string) {
    return pedir<{ ok: boolean; estado: string }>(`/hallazgos/${id}/estado`, conJson("POST", { estado, nota }));
  },

  publicarHallazgo(id: number, publicado: boolean) {
    return pedir<{ ok: boolean; publicado: boolean }>(`/hallazgos/${id}/publicar`, conJson("POST", { publicado }));
  },

  registrarRespuesta(id: number, texto: string) {
    return pedir<{ ok: boolean }>(`/hallazgos/${id}/respuesta`, conJson("POST", { texto }));
  },

  verConsorcio() {
    return pedir<ConsorcioInfo>("/consorcio");
  },

  editarConsorcio(cambio: Partial<Omit<ConsorcioInfo, "umbrales_default" | "umbrales">> & { umbrales?: Record<string, number> }) {
    return pedir<{ ok: boolean }>("/consorcio", conJson("PUT", cambio));
  },

  listarUnidades() {
    return pedir<UnidadFila[]>("/unidades");
  },

  generarCodigo(uf: number) {
    return pedir<{ uf: number; codigo: string }>(`/unidades/${uf}/codigo`, { method: "POST" });
  },

  listarDocumentos(liquidacionId: number) {
    const params = new URLSearchParams({ liquidacion_id: String(liquidacionId) });
    return pedir<DocumentoInfo[]>(`/documentos?${params.toString()}`);
  },

  miUnidad() {
    return pedir<MiUnidad>("/mi-unidad");
  },
};

export function urlInforme(periodo: string, tipo: "html" | "xlsx"): string {
  return `${BASE}/informes/${periodo}/${tipo}`;
}

export function urlContenidoDocumento(id: number, opts?: { vista?: boolean }): string {
  return `${BASE}/documentos/${id}/contenido${opts?.vista ? "?vista=1" : ""}`;
}
