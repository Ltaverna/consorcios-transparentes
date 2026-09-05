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
import { Skeleton } from "@/components/ui/skeleton";
import { FichaHallazgo } from "@/components/hallazgos/ficha";
import { documentosDelHallazgo } from "@/components/hallazgos/documentos-de";
import { api, ApiError, type DocumentoInfo, type HallazgoDetalle } from "@/lib/api";

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

  const cargar = useCallback(async (hallazgoId: number) => {
    setCargando(true);
    try {
      const det = await api.detalleHallazgo(hallazgoId);
      const docs = await api.listarDocumentos(det.liquidacion_id);
      setDetalle(det);
      setDocumentos(documentosDelHallazgo(det, docs));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    if (id === null) {
      setDetalle(null);
      setDocumentos([]);
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
          {cargando || !detalle ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : (
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
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
