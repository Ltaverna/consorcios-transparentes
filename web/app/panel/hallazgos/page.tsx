"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Kpi } from "@/components/kpi";
import { ListaHallazgos } from "@/components/hallazgos/lista";
import { DrawerHallazgo } from "@/components/hallazgos/drawer";
import { cn } from "@/lib/utils";
import { mensajeError, moneda } from "@/lib/formato";
import {
  api,
  type HallazgoResumen,
  type LiquidacionResumen,
} from "@/lib/api";

const SEVERIDADES = ["CRÍTICO", "ALTO", "MEDIO", "BAJO"];
const ESTADOS = ["pendiente", "preguntado", "respondido", "descartado", "cerrado"];

const PESO_SEVERIDAD: Record<string, number> = { "CRÍTICO": 0, ALTO: 1, MEDIO: 2, BAJO: 3 };

type Orden = "severidad" | "monto" | "fecha";
const ORDENES: { valor: Orden; texto: string }[] = [
  { valor: "severidad", texto: "Severidad" },
  { valor: "monto", texto: "Monto" },
  { valor: "fecha", texto: "Fecha" },
];

const CLASE_SELECT =
  "min-h-9 rounded-lg border border-borde-suave bg-white px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[#123A5C]";

function comparador(orden: Orden) {
  return (a: HallazgoResumen, b: HallazgoResumen): number => {
    if (orden === "monto") return b.monto - a.monto || b.id - a.id;
    if (orden === "fecha") return b.periodo.localeCompare(a.periodo) || b.id - a.id;
    const pesoA = PESO_SEVERIDAD[a.severidad] ?? 99;
    const pesoB = PESO_SEVERIDAD[b.severidad] ?? 99;
    return pesoA - pesoB || b.monto - a.monto || b.id - a.id;
  };
}

function hallazgos(n: number): string {
  return n === 1 ? "1 hallazgo" : `${n} hallazgos`;
}

function ChipFiltro({
  activo,
  texto,
  onClick,
}: {
  activo: boolean;
  texto: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={activo}
      onClick={onClick}
      className={cn(
        "min-h-9 inline-flex items-center rounded-full px-3.5 text-sm border transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-[#123A5C]",
        activo
          ? "bg-[#123A5C] text-white border-[#123A5C]"
          : "bg-white border-borde-suave hover:border-[#123A5C]"
      )}
    >
      {texto}
    </button>
  );
}

function GrupoFiltro({
  etiqueta,
  opciones,
  valores,
  alCambiar,
}: {
  etiqueta: string;
  opciones: string[];
  valores: string[];
  alCambiar: (v: string[]) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wide text-tinta-suave">{etiqueta}</span>
      <div className="flex flex-wrap gap-2">
        {opciones.map((op) => {
          const activo = valores.includes(op);
          return (
            <ChipFiltro
              key={op}
              texto={op}
              activo={activo}
              onClick={() => alCambiar(activo ? valores.filter((v) => v !== op) : [...valores, op])}
            />
          );
        })}
      </div>
    </div>
  );
}

function ContenidoHallazgos() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [filas, setFilas] = useState<HallazgoResumen[]>([]);
  const [liquidaciones, setLiquidaciones] = useState<LiquidacionResumen[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [abiertoId, setAbiertoId] = useState<number | null>(null);

  // Filtros multi-selección, restaurados desde la URL al montar.
  const [severidades, setSeveridades] = useState<string[]>(() => searchParams.getAll("severidad"));
  const [estados, setEstados] = useState<string[]>(() => searchParams.getAll("estado"));
  const [periodosElegidos, setPeriodosElegidos] = useState<string[]>(() => searchParams.getAll("periodo"));
  const [reglasElegidas, setReglasElegidas] = useState<string[]>(() => searchParams.getAll("regla"));
  const [busqueda, setBusqueda] = useState(() => searchParams.get("q") ?? "");
  const [orden, setOrden] = useState<Orden>(() => {
    const o = searchParams.get("orden");
    return o === "monto" || o === "fecha" ? o : "severidad";
  });

  // Selección para operaciones en lote.
  const [seleccionados, setSeleccionados] = useState<Set<number>>(new Set());
  const [estadoLote, setEstadoLote] = useState("preguntado");
  const [accionLote, setAccionLote] = useState<"estado" | "publicar" | null>(null);
  const [ejecutandoLote, setEjecutandoLote] = useState(false);

  // La carga trae todo sin filtros: los KPIs son globales y el filtrado es en memoria.
  const pedidoRef = useRef(0);
  const cargar = useCallback(async () => {
    const mio = ++pedidoRef.current;
    setCargando(true);
    setError(null);
    try {
      const res = await api.listarHallazgos();
      if (pedidoRef.current !== mio) return;
      setFilas(res);
    } catch (err) {
      if (pedidoRef.current !== mio) return;
      const mensaje = mensajeError(err);
      toast.error(mensaje);
      setError(mensaje);
    } finally {
      if (pedidoRef.current === mio) setCargando(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- patrón de carga establecido; ver plan Task 12
    cargar();
  }, [cargar]);

  useEffect(() => {
    api
      .listarLiquidaciones()
      .then(setLiquidaciones)
      .catch((err) => toast.error(mensajeError(err)));
  }, []);

  // Los filtros viven en la URL: sobreviven a navegar al detalle y volver.
  useEffect(() => {
    const p = new URLSearchParams();
    for (const v of severidades) p.append("severidad", v);
    for (const v of estados) p.append("estado", v);
    for (const v of periodosElegidos) p.append("periodo", v);
    for (const v of reglasElegidas) p.append("regla", v);
    if (busqueda) p.set("q", busqueda);
    if (orden !== "severidad") p.set("orden", orden);
    const qs = p.toString();
    if (qs !== searchParams.toString()) {
      router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
    }
  }, [severidades, estados, periodosElegidos, reglasElegidas, busqueda, orden, pathname, router, searchParams]);

  const periodos = Array.from(new Set(liquidaciones.map((l) => l.periodo))).sort().reverse();
  const reglas = useMemo(
    () => Array.from(new Set(filas.map((f) => f.regla))).sort(),
    [filas]
  );

  const filtradas = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    const lista = filas.filter(
      (f) =>
        (severidades.length === 0 || severidades.includes(f.severidad)) &&
        (estados.length === 0 || estados.includes(f.estado)) &&
        (periodosElegidos.length === 0 || periodosElegidos.includes(f.periodo)) &&
        (reglasElegidas.length === 0 || reglasElegidas.includes(f.regla)) &&
        (q === "" || f.titulo.toLowerCase().includes(q) || f.regla.toLowerCase().includes(q))
    );
    return lista.sort(comparador(orden));
  }, [filas, severidades, estados, periodosElegidos, reglasElegidas, busqueda, orden]);

  const totalFiltrado = filtradas.reduce((suma, f) => suma + f.monto, 0);

  // KPIs sobre el total, no sobre lo filtrado: siempre significan lo mismo.
  const criticos = filas.filter((f) => f.severidad === "CRÍTICO").length;
  const pendientes = filas.filter((f) => f.estado === "pendiente").length;
  const publicados = filas.filter((f) => f.publicado).length;

  // Tras un triage en el drawer: la fila se actualiza en memoria y la recarga
  // corre en segundo plano (la lista nunca se desmonta ni pierde el scroll).
  const alCambiarDrawer = useCallback(
    (actualizado?: HallazgoResumen) => {
      if (actualizado) {
        setFilas((previas) =>
          previas.map((f) =>
            f.id === actualizado.id
              ? { ...f, estado: actualizado.estado, publicado: actualizado.publicado }
              : f
          )
        );
      }
      cargar();
    },
    [cargar]
  );

  function alSeleccionar(id: number, marcado: boolean) {
    setSeleccionados((previos) => {
      const siguientes = new Set(previos);
      if (marcado) siguientes.add(id);
      else siguientes.delete(id);
      return siguientes;
    });
  }

  async function ejecutarLote() {
    if (!accionLote) return;
    const ids = Array.from(seleccionados);
    setEjecutandoLote(true);
    const fallidos: number[] = [];
    for (const id of ids) {
      try {
        if (accionLote === "estado") await api.cambiarEstado(id, estadoLote, "");
        else await api.publicarHallazgo(id, true);
      } catch {
        fallidos.push(id);
      }
    }
    setEjecutandoLote(false);
    setAccionLote(null);
    if (fallidos.length === 0) {
      toast.success(
        accionLote === "estado"
          ? `Se cambiaron ${hallazgos(ids.length)} a ${estadoLote}`
          : `Se marcaron ${hallazgos(ids.length)} para publicar`,
        { description: "Si el informe del período ya estaba publicado, volvé a publicarlo para que refleje este cambio." }
      );
      setSeleccionados(new Set());
    } else {
      toast.error(`${fallidos.length} de ${ids.length} fallaron; quedan seleccionados para reintentar`);
      setSeleccionados(new Set(fallidos));
    }
    cargar();
  }

  const primeraCarga = filas.length === 0 && cargando;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-titulos text-xl font-bold">Hallazgos</h1>

      <div className="grid grid-cols-3 gap-4">
        <Kpi etiqueta="Críticos" valor={String(criticos)} tono={criticos > 0 ? "critico" : "normal"} />
        <Kpi etiqueta="Pendientes" valor={String(pendientes)} />
        <Kpi etiqueta="Publicados" valor={String(publicados)} tono="exito" />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          aria-label="Buscar por título o regla"
          placeholder="Buscar por título o regla…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className={cn(CLASE_SELECT, "flex-1 min-w-48")}
        />
        <label className="flex items-center gap-2 text-sm text-tinta-suave">
          Ordenar por
          <select
            value={orden}
            onChange={(e) => setOrden(e.target.value as Orden)}
            className={cn(CLASE_SELECT, "text-tinta")}
          >
            {ORDENES.map((o) => (
              <option key={o.valor} value={o.valor}>{o.texto}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-6">
        <GrupoFiltro etiqueta="Severidad" opciones={SEVERIDADES} valores={severidades} alCambiar={setSeveridades} />
        <GrupoFiltro etiqueta="Estado" opciones={ESTADOS} valores={estados} alCambiar={setEstados} />
        {periodos.length > 0 && (
          <GrupoFiltro etiqueta="Período" opciones={periodos} valores={periodosElegidos} alCambiar={setPeriodosElegidos} />
        )}
        {reglas.length > 0 && (
          <GrupoFiltro etiqueta="Regla" opciones={reglas} valores={reglasElegidas} alCambiar={setReglasElegidas} />
        )}
      </div>

      {seleccionados.size > 0 && (
        <div
          role="toolbar"
          aria-label="Acciones en lote"
          className="sticky top-2 z-10 flex flex-wrap items-center gap-3 rounded-lg border border-[#123A5C] bg-white p-3 shadow-sm"
        >
          <span className="text-sm font-semibold">
            {seleccionados.size === 1 ? "1 seleccionado" : `${seleccionados.size} seleccionados`}
          </span>
          <label className="flex items-center gap-2 text-sm text-tinta-suave">
            Nuevo estado
            <select
              value={estadoLote}
              onChange={(e) => setEstadoLote(e.target.value)}
              className={cn(CLASE_SELECT, "text-tinta")}
            >
              {ESTADOS.map((e) => (
                <option key={e} value={e}>{e}</option>
              ))}
            </select>
          </label>
          <Button type="button" size="sm" variant="outline" onClick={() => setAccionLote("estado")}>
            Cambiar estado
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={() => setAccionLote("publicar")}>
            Publicar
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => {
              setSeleccionados(new Set());
              setAccionLote(null);
            }}
          >
            Quitar selección
          </Button>
          {accionLote && (
            <div className="flex w-full flex-wrap items-center gap-2 border-t border-borde-suave pt-2">
              <p className="text-sm">
                {accionLote === "estado" ? (
                  <>Cambiar {hallazgos(seleccionados.size)} a <strong>{estadoLote}</strong></>
                ) : (
                  <>Publicar {hallazgos(seleccionados.size)} en el informe</>
                )}
              </p>
              <Button type="button" size="sm" onClick={ejecutarLote} disabled={ejecutandoLote}>
                {ejecutandoLote ? "Aplicando…" : "Confirmar"}
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={() => setAccionLote(null)} disabled={ejecutandoLote}>
                Cancelar
              </Button>
            </div>
          )}
        </div>
      )}

      {!primeraCarga && !error && (
        <p className="text-sm text-tinta-suave">
          {filtradas.length === filas.length
            ? `${hallazgos(filas.length)} · ${moneda(totalFiltrado)}`
            : `Mostrando ${filtradas.length} de ${hallazgos(filas.length)} · ${moneda(totalFiltrado)}`}
        </p>
      )}

      {primeraCarga ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : error && filas.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-tinta-suave">{error}</p>
            <Button variant="outline" onClick={cargar}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : (
        <ListaHallazgos
          filas={filtradas}
          alAbrir={setAbiertoId}
          seleccionados={seleccionados}
          alSeleccionar={alSeleccionar}
        />
      )}

      <DrawerHallazgo
        id={abiertoId}
        alCerrar={() => setAbiertoId(null)}
        alCambiar={alCambiarDrawer}
      />
    </div>
  );
}

export default function HallazgosPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col gap-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      }
    >
      <ContenidoHallazgos />
    </Suspense>
  );
}
