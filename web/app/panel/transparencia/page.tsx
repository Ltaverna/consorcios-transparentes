"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { COMPONENTES_INDICE, cuentaPenalizacion, mensajeError, moneda, puntosIndice } from "@/lib/formato";
import { api, type IndiceTransparencia, type StatsTransparencia, type GastoConEstado } from "@/lib/api";
import { ChipEstadoGasto } from "@/components/estado-gasto";
import { ChipSeveridad } from "@/components/severidad";

// ---- helpers

const ORDEN_ESTADOS = ["verificado", "requiere_explicacion", "anomalia", "inconsistencia", "sin_informacion"];
const ORDEN_SEVERIDADES = ["CRÍTICO", "ALTO", "MEDIO", "BAJO"];

function porcentaje(v: number): string {
  return `${Math.round(v * 100)} %`;
}

// ---- sub-componentes

function Barra({ etiqueta, pct, importe }: { etiqueta: string; pct: number; importe: number }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between text-sm">
        <span>{etiqueta}</span>
        <span className="tabular-nums text-tinta-suave">
          {porcentaje(pct)} · {moneda(importe)}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-[#E2E8F0]">
        <div
          className="h-2 rounded-full bg-[#123A5C]"
          style={{ width: `${Math.min(100, Math.max(0, pct * 100))}%` }}
        />
      </div>
    </div>
  );
}

function CardIndice({ datos }: { datos: IndiceTransparencia }) {
  const t = datos.totales;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Índice de transparencia</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-baseline gap-3">
          <span className="font-titulos text-5xl font-bold tabular-nums">{datos.indice}</span>
          <span className="text-tinta-suave">/ 100</span>
          <span className="ml-auto text-sm text-tinta-suave tabular-nums">
            {datos.rango.desde} → {datos.rango.hasta}
          </span>
        </div>
        <p className="text-sm text-tinta-suave">
          {t.componentes
            ? "Índice compuesto: cinco componentes ponderados, menos una penalización por cuestiones críticas abiertas."
            : "Porcentaje del dinero trazable: gastos con respaldo documental y sin ninguna cuestión abierta."}
        </p>
        <div className="flex flex-col gap-3">
          <Barra etiqueta="Dinero verificado" pct={t.pct_trazable} importe={t.dinero_verificado} />
          <Barra etiqueta="Con factura adjunta" pct={t.pct_con_factura} importe={t.dinero_con_factura} />
          <Barra etiqueta="Pagos respaldados" pct={t.pct_pago_respaldado} importe={t.dinero_pago_respaldado} />
        </div>
        {t.componentes ? (
          <div className="flex flex-col gap-2">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-tinta-suave">
                  <th className="pb-1.5 pr-4 font-medium">Componente</th>
                  <th className="pb-1.5 pr-4 font-medium text-right">Valor</th>
                  <th className="pb-1.5 pr-4 font-medium text-right">Peso</th>
                  <th className="pb-1.5 font-medium text-right">Puntos</th>
                </tr>
              </thead>
              <tbody>
                {COMPONENTES_INDICE.filter(({ clave }) => t.componentes![clave]).map(({ clave, etiqueta }) => {
                  const c = t.componentes![clave];
                  return (
                    <tr key={clave} className="border-b last:border-0">
                      <td className="py-1.5 pr-4">
                        {etiqueta}
                        {c.periodos_cuadran !== undefined && c.periodos_totales !== undefined && (
                          <span className="text-xs text-tinta-suave">
                            {" "}({c.periodos_cuadran} de {c.periodos_totales} períodos cuadran)
                          </span>
                        )}
                      </td>
                      <td className="py-1.5 pr-4 text-right tabular-nums">{porcentaje(c.valor)}</td>
                      <td className="py-1.5 pr-4 text-right tabular-nums">{porcentaje(c.peso)}</td>
                      <td className="py-1.5 text-right tabular-nums">{puntosIndice(c.puntos)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {t.penalizacion && (
              <p className="text-sm tabular-nums">
                Penalización: {cuentaPenalizacion(t.penalizacion)}
                {t.penalizacion.criticos_abiertos > 0 && <> · −{t.penalizacion.puntos} puntos</>}
              </p>
            )}
            <p className="text-xs text-tinta-suave">
              índice = suma de puntos − penalización, recortado a 0-100 · ninguna cifra la genera una IA
            </p>
          </div>
        ) : (
          <p className="text-xs text-tinta-suave">
            Fórmula: índice = dinero verificado ÷ dinero total × 100 = {moneda(t.dinero_verificado)} ÷{" "}
            {moneda(t.dinero_total)}. Cifras calculadas del cruce de documentos, sin intervención de IA.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function CardEstados({
  stats,
  seleccionado,
  onElegir,
}: {
  stats: StatsTransparencia;
  seleccionado: string | null;
  onElegir: (estado: string) => void;
}) {
  const filas = ORDEN_ESTADOS.filter((e) => stats.gastos_por_estado[e]);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Estados de los gastos</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        {filas.length === 0 ? (
          <p className="text-sm text-tinta-suave">Sin datos</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-tinta-suave">
                <th className="pb-2 pr-4 font-medium">Estado</th>
                <th className="pb-2 pr-4 font-medium text-right">Cant.</th>
                <th className="pb-2 font-medium text-right">Importe</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((estado) => {
                const { cantidad, importe } = stats.gastos_por_estado[estado];
                return (
                  <tr
                    key={estado}
                    onClick={() => onElegir(estado)}
                    className={`cursor-pointer border-b last:border-0 hover:bg-black/5 ${
                      seleccionado === estado ? "bg-black/5" : ""
                    }`}
                  >
                    <td className="py-1.5 pr-4">
                      <ChipEstadoGasto estado={estado} />
                    </td>
                    <td className="py-1.5 pr-4 text-right tabular-nums">{cantidad}</td>
                    <td className="py-1.5 text-right tabular-nums">{moneda(importe)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <p className="mt-2 text-xs text-tinta-suave">
          Hacé clic en un estado para ver los gastos; otro clic saca el filtro.
        </p>
      </CardContent>
    </Card>
  );
}

function CardGastos({
  periodos,
  periodo,
  onPeriodo,
  gastos,
  cargando,
  estadoFiltro,
}: {
  periodos: string[];
  periodo: string;
  onPeriodo: (p: string) => void;
  gastos: GastoConEstado[] | null;
  cargando: boolean;
  estadoFiltro: string | null;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Gastos del período</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5 self-start">
          <Label htmlFor="periodo-transparencia">Período</Label>
          <select
            id="periodo-transparencia"
            value={periodo}
            onChange={(e) => onPeriodo(e.target.value)}
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs"
          >
            {periodos.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        {cargando ? (
          <Skeleton className="h-24 w-full" />
        ) : !gastos || gastos.length === 0 ? (
          <p className="text-sm text-tinta-suave">
            {estadoFiltro ? "Sin gastos en ese estado para el período." : "Sin gastos para el período."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-tinta-suave">
                  <th className="pb-2 pr-4 font-medium">N°</th>
                  <th className="pb-2 pr-4 font-medium">Proveedor</th>
                  <th className="pb-2 pr-4 font-medium text-right">Importe</th>
                  <th className="pb-2 pr-4 font-medium">Estado</th>
                  <th className="pb-2 pr-4 font-medium">Hallazgos abiertos</th>
                  <th className="pb-2 font-medium">Documentos</th>
                </tr>
              </thead>
              <tbody>
                {gastos.map((g) => (
                  <tr key={g.n} className="border-b align-top last:border-0">
                    <td className="py-1.5 pr-4 tabular-nums">{g.n}</td>
                    <td className="py-1.5 pr-4">
                      <span className="font-mono text-xs">{g.proveedor}</span>
                      <span className="block text-xs text-tinta-suave">{g.concepto}</span>
                    </td>
                    <td className="py-1.5 pr-4 text-right tabular-nums">{moneda(g.importe)}</td>
                    <td className="py-1.5 pr-4">
                      <ChipEstadoGasto estado={g.estado} />
                    </td>
                    <td className="py-1.5 pr-4">
                      {g.hallazgos.length === 0 ? (
                        <span className="text-xs text-tinta-suave">—</span>
                      ) : (
                        <ul className="flex flex-col gap-1">
                          {g.hallazgos.map((h) => (
                            <li key={h.id} className="flex items-center gap-2">
                              <ChipSeveridad severidad={h.severidad} />
                              <span>{h.titulo}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                    <td className="py-1.5">
                      {g.documentos.length === 0 ? (
                        <span className="text-xs text-tinta-suave">—</span>
                      ) : (
                        <ul className="flex flex-col gap-1">
                          {g.documentos.map((d) => (
                            <li key={d.id} className="font-mono text-xs">
                              {d.archivo}
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CardCuestiones({ stats }: { stats: StatsTransparencia }) {
  const abiertos = ORDEN_SEVERIDADES.filter((s) => (stats.hallazgos_abiertos[s] ?? 0) > 0);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cuestiones</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2 text-sm">
        {abiertos.length === 0 ? (
          <p className="text-tinta-suave">Sin cuestiones abiertas.</p>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            {abiertos.map((s) => (
              <span key={s} className="flex items-center gap-1.5">
                <ChipSeveridad severidad={s} />
                <span className="tabular-nums">{stats.hallazgos_abiertos[s]}</span>
              </span>
            ))}
          </div>
        )}
        <p className="text-tinta-suave">
          Resueltas: <span className="tabular-nums">{stats.hallazgos_resueltos}</span>
        </p>
      </CardContent>
    </Card>
  );
}

// ---- página principal

export default function PaginaTransparencia() {
  const [datos, setDatos] = useState<IndiceTransparencia | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [periodo, setPeriodo] = useState("");
  const [estadoFiltro, setEstadoFiltro] = useState<string | null>(null);
  const [gastos, setGastos] = useState<GastoConEstado[] | null>(null);
  const [cargandoGastos, setCargandoGastos] = useState(false);

  const cargarGastos = useCallback(async (p: string, estado?: string) => {
    setCargandoGastos(true);
    try {
      const res = await api.gastosTransparencia(p, estado);
      setGastos(res.gastos);
    } catch (err) {
      toast.error(mensajeError(err));
    } finally {
      setCargandoGastos(false);
    }
  }, []);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const res = await api.indiceTransparencia();
      setDatos(res);
      const ultimo = res.periodos.at(-1)?.periodo;
      if (ultimo) {
        setPeriodo(ultimo);
        setEstadoFiltro(null);
        await cargarGastos(ultimo);
      }
    } catch (err) {
      const mensaje = mensajeError(err);
      toast.error(mensaje);
      setError(mensaje);
    } finally {
      setCargando(false);
    }
  }, [cargarGastos]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- patrón de carga establecido; ver plan Task 12
    cargar();
  }, [cargar]);

  function cambiarPeriodo(p: string) {
    setPeriodo(p);
    setEstadoFiltro(null);
    cargarGastos(p);
  }

  function elegirEstado(estado: string) {
    const nuevo = estadoFiltro === estado ? null : estado;
    setEstadoFiltro(nuevo);
    cargarGastos(periodo, nuevo ?? undefined);
  }

  const statsPeriodo = datos?.periodos.find((p) => p.periodo === periodo) ?? datos?.totales;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-titulos text-xl font-bold">Transparencia</h1>

      {cargando ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : error || !datos ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-tinta-suave">{error ?? "No se pudo cargar el índice"}</p>
            <Button variant="outline" onClick={cargar}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : datos.periodos.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-tinta-suave">Todavía no hay períodos analizados.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <CardIndice datos={datos} />
          {statsPeriodo && (
            <CardEstados stats={statsPeriodo} seleccionado={estadoFiltro} onElegir={elegirEstado} />
          )}
          <CardGastos
            periodos={datos.periodos.map((p) => p.periodo ?? "")}
            periodo={periodo}
            onPeriodo={cambiarPeriodo}
            gastos={gastos}
            cargando={cargandoGastos}
            estadoFiltro={estadoFiltro}
          />
          <CardCuestiones stats={datos.totales} />
        </>
      )}
    </div>
  );
}
