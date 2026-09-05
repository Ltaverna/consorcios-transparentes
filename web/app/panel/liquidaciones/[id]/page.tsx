"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DetalleLiquidacion } from "@/components/liquidaciones/detalle";
import {
  api,
  ApiError,
  type DocumentoInfo,
  type HallazgoResumen,
  type LiquidacionDetalle,
} from "@/lib/api";

function PublicarInforme({
  liquidacionId,
  periodo,
  alPublicar,
}: {
  liquidacionId: number;
  periodo: string;
  alPublicar: () => void;
}) {
  const [cargando, setCargando] = useState(false);
  const [hallazgos, setHallazgos] = useState<HallazgoResumen[] | null>(null);
  const [publicando, setPublicando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function alAbrir(abierto: boolean) {
    if (!abierto) return;
    setError(null);
    setHallazgos(null);
    setCargando(true);
    try {
      const res = await api.listarHallazgos({ periodo });
      setHallazgos(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }

  async function confirmar() {
    setError(null);
    setPublicando(true);
    try {
      const res = await api.publicarLiquidacion(liquidacionId);
      toast.success(`Se publicaron ${res.hallazgos_publicados} hallazgos`);
      alPublicar();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setPublicando(false);
    }
  }

  const publicados = hallazgos?.filter((h) => h.publicado) ?? [];

  return (
    <Dialog onOpenChange={alAbrir}>
      <DialogTrigger render={<Button />}>Publicar informe</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Publicar informe de {periodo}</DialogTitle>
        </DialogHeader>
        {cargando ? (
          <Skeleton className="h-20 w-full" />
        ) : hallazgos ? (
          publicados.length > 0 ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm">Van a publicarse {publicados.length} hallazgos:</p>
              <ul className="list-disc pl-5 text-sm">
                {publicados.map((h) => (
                  <li key={h.id}>{h.titulo}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-[#B45309] bg-[#FEF3C7] rounded-lg p-3">
              Ningún hallazgo está marcado para publicar — el informe saldrá sin hallazgos.
            </p>
          )
        ) : null}
        {error && (
          <p role="alert" className="text-[#B42318] text-sm">
            {error}
          </p>
        )}
        <Button onClick={confirmar} disabled={publicando || cargando}>
          {publicando ? "Publicando…" : "Confirmar"}
        </Button>
      </DialogContent>
    </Dialog>
  );
}

export default function LiquidacionDetallePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const liquidacionId = Number(id);

  const [detalle, setDetalle] = useState<LiquidacionDetalle | null>(null);
  const [documentos, setDocumentos] = useState<DocumentoInfo[]>([]);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const [det, docs] = await Promise.all([
        api.detalleLiquidacion(liquidacionId),
        api.listarDocumentos(liquidacionId),
      ]);
      setDetalle(det);
      setDocumentos(docs);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }, [liquidacionId]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  return (
    <div className="flex flex-col gap-4">
      <Link href="/panel/liquidaciones" className="text-sm underline">
        ← Liquidaciones
      </Link>
      {cargando || !detalle ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <h1 className="font-titulos text-xl font-bold">Liquidación {detalle.periodo}</h1>
            {(detalle.estado === "procesada" || detalle.estado === "publicada") && (
              <PublicarInforme
                liquidacionId={detalle.id}
                periodo={detalle.periodo}
                alPublicar={cargar}
              />
            )}
          </div>
          <DetalleLiquidacion detalle={detalle} documentos={documentos} />
        </>
      )}
    </div>
  );
}
