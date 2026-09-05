"use client";

import { useId, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { mensajeError } from "@/lib/formato";

/** Botón + diálogo para subir el ZIP de comprobantes de una liquidación y cruzarlos. */
export function SubirComprobantes({
  liquidacionId,
  periodo,
  alCambiar,
}: {
  liquidacionId: number;
  periodo: string;
  alCambiar: () => void;
}) {
  const idArchivo = useId();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<{ documentos: number; hallazgos_cruce: number } | null>(null);

  async function alEnviar(e: React.FormEvent) {
    e.preventDefault();
    if (!archivo) return;
    setError(null);
    setEnviando(true);
    try {
      const res = await api.subirComprobantes(liquidacionId, archivo);
      setResultado(res);
      alCambiar();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Dialog>
      <DialogTrigger render={<Button variant="outline" size="sm" />}>
        Comprobantes
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Comprobantes de {periodo}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-tinta-suave">
          Subí el ZIP que genera <code>ct descargar</code> (hasta 100 MB).
        </p>
        <form onSubmit={alEnviar} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={idArchivo}>ZIP de comprobantes</Label>
            <input
              type="file"
              accept=".zip"
              id={idArchivo}
              className="text-sm"
              onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
            />
          </div>
          <Button type="submit" disabled={enviando || !archivo}>
            {enviando ? "Subiendo…" : "Subir y cruzar"}
          </Button>
        </form>
        {resultado && (
          <p className="text-sm text-tinta-suave">
            Se leyeron {resultado.documentos} documentos y el cruce generó {resultado.hallazgos_cruce} hallazgos.
          </p>
        )}
        {error && (
          <p role="alert" className="text-[#B42318] text-sm">
            {error}
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
