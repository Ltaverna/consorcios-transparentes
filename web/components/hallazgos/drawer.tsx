"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FichaHallazgo } from "@/components/hallazgos/ficha";
import { documentosDelHallazgo } from "@/components/hallazgos/documentos-de";
import { mensajeError } from "@/lib/formato";
import { api, type DocumentoInfo, type HallazgoDetalle } from "@/lib/api";

/** Drawer lateral de triage: carga el detalle de un hallazgo y su ficha. */
export function DrawerHallazgo({
  id,
  alCerrar,
  alCambiar,
}: {
  id: number | null;
  alCerrar: () => void;
  alCambiar: () => void;
}) {
  const [detalle, setDetalle] = useState<HallazgoDetalle | null>(null);
  const [documentos, setDocumentos] = useState<DocumentoInfo[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async (hallazgoId: number) => {
    setCargando(true);
    setError(null);
    try {
      const det = await api.detalleHallazgo(hallazgoId);
      const docs = await api.listarDocumentos(det.liquidacion_id);
      setDetalle(det);
      setDocumentos(documentosDelHallazgo(det, docs));
    } catch (err) {
      const mensaje = mensajeError(err);
      toast.error(mensaje);
      setError(mensaje);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    if (id === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- patrón de carga establecido; ver plan Task 12
      setDetalle(null);
      setDocumentos([]);
      setError(null);
      return;
    }
    cargar(id);
  }, [id, cargar]);

  return (
    <Sheet open={id !== null} onOpenChange={(abierto) => !abierto && alCerrar()}>
      <SheetContent side="right" className="sm:max-w-xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Hallazgo</SheetTitle>
        </SheetHeader>
        <div className="px-4 pb-4 flex flex-col gap-4">
          {cargando ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-tinta-suave">{error}</p>
              <Button variant="outline" onClick={() => id !== null && cargar(id)}>
                Reintentar
              </Button>
            </div>
          ) : detalle ? (
            <>
              <FichaHallazgo
                detalle={detalle}
                documentos={documentos}
                alCambiar={() => {
                  if (id !== null) cargar(id);
                  alCambiar();
                }}
                conVisor={false}
              />
              <Link href={`/panel/hallazgos/${detalle.id}`} className="text-sm underline">
                Abrir completo →
              </Link>
            </>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
