"use client";

import { useCallback, useEffect, useState } from "react";
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
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRol } from "@/components/rol-context";
import { DetalleLiquidacion } from "@/components/liquidaciones/detalle";
import { mensajeError } from "@/lib/formato";
import {
  api,
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
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [hallazgos, setHallazgos] = useState<HallazgoResumen[] | null>(null);
  const [publicando, setPublicando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function alAbrir(abierto: boolean) {
    setAbierto(abierto);
    if (!abierto) return;
    setError(null);
    setHallazgos(null);
    setCargando(true);
    try {
      const res = await api.listarHallazgos({ periodo });
      setHallazgos(res);
    } catch (err) {
      setError(mensajeError(err));
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
      setAbierto(false);
      alPublicar();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setPublicando(false);
    }
  }

  const publicados = hallazgos?.filter((h) => h.publicado) ?? [];

  return (
    <Dialog open={abierto} onOpenChange={alAbrir}>
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
            <p className="text-sm text-[#93540B] bg-[#FEF0C7] rounded-lg p-3">
              Ningún hallazgo está marcado para publicar — el informe saldrá sin hallazgos.
            </p>
          )
        ) : null}
        {error && (
          <p role="alert" className="text-[#B42318] text-sm">
            {error}
          </p>
        )}
        {/* un error previo no bloquea el botón: publicar se puede reintentar */}
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
  const rol = useRol();
  const [detalle, setDetalle] = useState<LiquidacionDetalle | null>(null);
  const [documentos, setDocumentos] = useState<DocumentoInfo[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { id } = await params;
      const liquidacionId = Number(id);
      const [det, docs] = await Promise.all([
        api.detalleLiquidacion(liquidacionId),
        api.listarDocumentos(liquidacionId),
      ]);
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

  return (
    <div className="flex flex-col gap-4">
      <Link href="/panel/liquidaciones" className="text-sm underline">
        ← Liquidaciones
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
        <>
          <div className="flex items-center justify-between">
            <h1 className="font-titulos text-xl font-bold">Liquidación {detalle.periodo}</h1>
            {rol === "auditor" && (detalle.estado === "procesada" || detalle.estado === "publicada") && (
              <PublicarInforme
                liquidacionId={detalle.id}
                periodo={detalle.periodo}
                alPublicar={cargar}
              />
            )}
          </div>
          <DetalleLiquidacion detalle={detalle} documentos={documentos} />
        </>
      ) : null}
    </div>
  );
}
