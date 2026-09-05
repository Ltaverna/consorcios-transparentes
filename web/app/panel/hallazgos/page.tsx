"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Kpi } from "@/components/kpi";
import { ListaHallazgos } from "@/components/hallazgos/lista";
import { DrawerHallazgo } from "@/components/hallazgos/drawer";
import { cn } from "@/lib/utils";
import {
  api,
  ApiError,
  type HallazgoResumen,
  type LiquidacionResumen,
} from "@/lib/api";

const SEVERIDADES = ["CRÍTICO", "ALTO", "MEDIO", "BAJO"];
const ESTADOS = ["pendiente", "preguntado", "respondido", "descartado", "cerrado"];

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
  valor,
  alElegir,
}: {
  etiqueta: string;
  opciones: string[];
  valor: string | null;
  alElegir: (v: string | null) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wide text-tinta-suave">{etiqueta}</span>
      <div className="flex flex-wrap gap-2">
        {opciones.map((op) => (
          <ChipFiltro
            key={op}
            texto={op}
            activo={valor === op}
            onClick={() => alElegir(valor === op ? null : op)}
          />
        ))}
      </div>
    </div>
  );
}

export default function HallazgosPage() {
  const [filas, setFilas] = useState<HallazgoResumen[]>([]);
  const [liquidaciones, setLiquidaciones] = useState<LiquidacionResumen[]>([]);
  const [cargando, setCargando] = useState(true);
  const [abiertoId, setAbiertoId] = useState<number | null>(null);

  const [severidad, setSeveridad] = useState<string | null>(null);
  const [estado, setEstado] = useState<string | null>(null);
  const [periodo, setPeriodo] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const res = await api.listarHallazgos({
        severidad: severidad ?? undefined,
        estado: estado ?? undefined,
        periodo: periodo ?? undefined,
      });
      setFilas(res);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }, [severidad, estado, periodo]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  useEffect(() => {
    api
      .listarLiquidaciones()
      .then(setLiquidaciones)
      .catch((err) => toast.error(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor"));
  }, []);

  const periodos = Array.from(new Set(liquidaciones.map((l) => l.periodo))).sort().reverse();

  const criticos = filas.filter((f) => f.severidad === "CRÍTICO").length;
  const pendientes = filas.filter((f) => f.estado === "pendiente").length;
  const publicados = filas.filter((f) => f.publicado).length;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-titulos text-xl font-bold">Hallazgos</h1>

      <div className="grid grid-cols-3 gap-4">
        <Kpi etiqueta="Críticos" valor={String(criticos)} tono={criticos > 0 ? "critico" : "normal"} />
        <Kpi etiqueta="Pendientes" valor={String(pendientes)} />
        <Kpi etiqueta="Publicados" valor={String(publicados)} tono="exito" />
      </div>

      <div className="flex flex-wrap gap-6">
        <GrupoFiltro etiqueta="Severidad" opciones={SEVERIDADES} valor={severidad} alElegir={setSeveridad} />
        <GrupoFiltro etiqueta="Estado" opciones={ESTADOS} valor={estado} alElegir={setEstado} />
        {periodos.length > 0 && (
          <GrupoFiltro etiqueta="Período" opciones={periodos} valor={periodo} alElegir={setPeriodo} />
        )}
      </div>

      {cargando ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : (
        <ListaHallazgos filas={filas} alAbrir={setAbiertoId} />
      )}

      <DrawerHallazgo
        id={abiertoId}
        alCerrar={() => setAbiertoId(null)}
        alCambiar={cargar}
      />
    </div>
  );
}
