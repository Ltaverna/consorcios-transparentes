"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { SubirLiquidacion } from "@/components/liquidaciones/subir-liquidacion";
import { ListaLiquidaciones } from "@/components/liquidaciones/lista";
import { api, ApiError, type LiquidacionResumen } from "@/lib/api";

export default function LiquidacionesPage() {
  const [filas, setFilas] = useState<LiquidacionResumen[]>([]);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    try {
      const res = await api.listarLiquidaciones();
      setFilas(res);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  useEffect(() => {
    if (!filas.some((f) => f.estado === "procesando")) return;
    const id = setInterval(cargar, 2000);
    return () => clearInterval(id);
  }, [filas, cargar]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-titulos text-xl font-bold">Liquidaciones</h1>
      <SubirLiquidacion alSubir={cargar} />
      {cargando ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : (
        <ListaLiquidaciones filas={filas} alCambiar={cargar} />
      )}
    </div>
  );
}
