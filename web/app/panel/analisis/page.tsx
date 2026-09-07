"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mensajeError, moneda } from "@/lib/formato";
import { api, type GrupoAgregado, type GastoConsulta } from "@/lib/api";

// ---- helpers

function variacionTexto(v: number | null): string {
  if (v === null) return "—";
  const signo = v >= 0 ? "+" : "";
  return `${signo}${Math.round(v * 100)} %`;
}

function variacionClase(v: number | null): string {
  if (v === null) return "";
  return v > 0 ? "text-[#B42318]" : v < 0 ? "text-[#1B7A43]" : "";
}

// ---- sub-componentes

function TablaAgregados({ grupos, titulo }: { grupos: GrupoAgregado[]; titulo: string }) {
  if (grupos.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{titulo}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-tinta-suave">Sin datos</p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>{titulo}</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-tinta-suave">
              <th className="pb-2 pr-4 font-medium">Nombre</th>
              <th className="pb-2 pr-4 font-medium text-right">Total</th>
              <th className="pb-2 pr-4 font-medium text-right">Cant.</th>
              <th className="pb-2 font-medium text-right">Var.</th>
            </tr>
          </thead>
          <tbody>
            {grupos.map((g) => (
              <tr key={g.clave} className="border-b last:border-0">
                <td className="py-1.5 pr-4 font-mono text-xs">{g.clave}</td>
                <td className="py-1.5 pr-4 text-right tabular-nums">{moneda(g.total)}</td>
                <td className="py-1.5 pr-4 text-right tabular-nums">{g.cantidad}</td>
                <td className={`py-1.5 text-right tabular-nums ${variacionClase(g.variacion)}`}>
                  {variacionTexto(g.variacion)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

interface FiltrosBusqueda {
  proveedor: string;
  q: string;
  importe_min: string;
  periodo_desde: string;
  periodo_hasta: string;
}

function CardBusqueda() {
  const [filtros, setFiltros] = useState<FiltrosBusqueda>({
    proveedor: "",
    q: "",
    importe_min: "",
    periodo_desde: "",
    periodo_hasta: "",
  });
  const [buscando, setBuscando] = useState(false);
  const [resultado, setResultado] = useState<{ filas: GastoConsulta[]; total: number; cantidad: number } | null>(null);

  function setFiltro(clave: keyof FiltrosBusqueda) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setFiltros((f) => ({ ...f, [clave]: e.target.value }));
  }

  async function buscar(e: React.FormEvent) {
    e.preventDefault();
    setBuscando(true);
    try {
      const params: Parameters<typeof api.consultarGastos>[0] = {};
      if (filtros.proveedor) params.proveedor = filtros.proveedor;
      if (filtros.q) params.q = filtros.q;
      if (filtros.importe_min) params.importe_min = Number(filtros.importe_min);
      if (filtros.periodo_desde) params.periodo_desde = filtros.periodo_desde;
      if (filtros.periodo_hasta) params.periodo_hasta = filtros.periodo_hasta;
      setResultado(await api.consultarGastos(params));
    } catch (err) {
      toast.error(mensajeError(err));
    } finally {
      setBuscando(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Buscar gastos</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <form onSubmit={buscar} className="flex flex-col gap-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="busqueda-proveedor">Proveedor</Label>
              <Input
                id="busqueda-proveedor"
                value={filtros.proveedor}
                onChange={setFiltro("proveedor")}
                placeholder="Nombre parcial…"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="busqueda-texto">Texto</Label>
              <Input
                id="busqueda-texto"
                value={filtros.q}
                onChange={setFiltro("q")}
                placeholder="Concepto, factura…"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="busqueda-importe">Importe mínimo</Label>
              <Input
                id="busqueda-importe"
                type="number"
                value={filtros.importe_min}
                onChange={setFiltro("importe_min")}
                placeholder="0"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="busqueda-desde">Desde</Label>
              {/* type="month" da AAAA-MM (lo que espera la API); pattern y placeholder cubren navegadores sin selector de mes */}
              <Input
                id="busqueda-desde"
                type="month"
                pattern="\d{4}-\d{2}"
                value={filtros.periodo_desde}
                onChange={setFiltro("periodo_desde")}
                placeholder="2026-01"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="busqueda-hasta">Hasta</Label>
              <Input
                id="busqueda-hasta"
                type="month"
                pattern="\d{4}-\d{2}"
                value={filtros.periodo_hasta}
                onChange={setFiltro("periodo_hasta")}
                placeholder="2026-12"
              />
            </div>
          </div>
          <Button type="submit" disabled={buscando} className="self-start">
            {buscando ? "Buscando…" : "Buscar"}
          </Button>
        </form>

        {resultado && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-tinta-suave" data-testid="total-busqueda">
              {resultado.cantidad} gasto{resultado.cantidad !== 1 ? "s" : ""} · total {moneda(resultado.total)}
            </p>
            {resultado.filas.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs text-tinta-suave">
                      <th className="pb-2 pr-4 font-medium">Período</th>
                      <th className="pb-2 pr-4 font-medium">Proveedor</th>
                      <th className="pb-2 pr-4 font-medium">Concepto</th>
                      <th className="pb-2 font-medium text-right">Importe</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultado.filas.map((f) => (
                      <tr key={`${f.periodo}-${f.n}`} className="border-b last:border-0">
                        <td className="py-1.5 pr-4 tabular-nums">{f.periodo}</td>
                        <td className="py-1.5 pr-4 font-mono text-xs">{f.proveedor}</td>
                        <td className="py-1.5 pr-4">{f.concepto}</td>
                        <td className="py-1.5 text-right tabular-nums">{moneda(f.importe)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---- página principal

export default function PaginaAnalisis() {
  const [proveedores, setProveedores] = useState<GrupoAgregado[] | null>(null);
  const [categorias, setCategorias] = useState<GrupoAgregado[] | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const [resProv, resCat] = await Promise.all([
        api.agregados("proveedor"),
        api.agregados("categoria"),
      ]);
      setProveedores(resProv.grupos);
      setCategorias(resCat.grupos);
    } catch (err) {
      const mensaje = mensajeError(err);
      toast.error(mensaje);
      setError(mensaje);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- patrón de carga establecido; ver plan Task 12
    cargar();
  }, [cargar]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-titulos text-xl font-bold">Análisis</h1>

      {cargando ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-tinta-suave">{error}</p>
            <Button variant="outline" onClick={cargar}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <TablaAgregados grupos={proveedores ?? []} titulo="Proveedores" />
          <TablaAgregados grupos={categorias ?? []} titulo="Categorías" />
          <CardBusqueda />
        </>
      )}
    </div>
  );
}
