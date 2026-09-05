"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { FichaHallazgo } from "@/components/hallazgos/ficha";
import { documentosDelHallazgo } from "@/components/hallazgos/documentos-de";
import { api, ApiError, type DocumentoInfo, type HallazgoDetalle } from "@/lib/api";

export default function PaginaHallazgo({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [detalle, setDetalle] = useState<HallazgoDetalle | null>(null);
  const [documentos, setDocumentos] = useState<DocumentoInfo[]>([]);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const { id } = await params;
      const det = await api.detalleHallazgo(Number(id));
      const docs = await api.listarDocumentos(det.liquidacion_id);
      setDetalle(det);
      setDocumentos(docs);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }, [params]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const docsDelHallazgo = detalle ? documentosDelHallazgo(detalle, documentos) : [];

  return (
    <div className="flex flex-col gap-4">
      <Link href="/panel/hallazgos" className="text-sm underline">
        ← Hallazgos
      </Link>
      {cargando || !detalle ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        <FichaHallazgo
          detalle={detalle}
          documentos={docsDelHallazgo}
          alCambiar={cargar}
          conVisor
        />
      )}
    </div>
  );
}
