"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FichaHallazgo } from "@/components/hallazgos/ficha";
import { documentosDelHallazgo } from "@/components/hallazgos/documentos-de";
import { mensajeError } from "@/lib/formato";
import { api, type DocumentoInfo, type HallazgoDetalle } from "@/lib/api";

export default function PaginaHallazgo({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [detalle, setDetalle] = useState<HallazgoDetalle | null>(null);
  const [documentos, setDocumentos] = useState<DocumentoInfo[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { id } = await params;
      const det = await api.detalleHallazgo(Number(id));
      const docs = await api.listarDocumentos(det.liquidacion_id);
      setDetalle(det);
      setDocumentos(docs);
    } catch (err) {
      const mensaje = mensajeError(err);
      toast.error(mensaje);
      setError(mensaje);
    } finally {
      setCargando(false);
    }
  }, [params]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- patrón de carga establecido; ver plan Task 12
    cargar();
  }, [cargar]);

  const docsDelHallazgo = detalle ? documentosDelHallazgo(detalle, documentos) : [];

  return (
    <div className="flex flex-col gap-4">
      <Link href="/panel/hallazgos" className="text-sm underline">
        ← Hallazgos
      </Link>
      {cargando ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
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
      ) : detalle ? (
        <FichaHallazgo
          detalle={detalle}
          documentos={docsDelHallazgo}
          alCambiar={cargar}
        />
      ) : null}
    </div>
  );
}
