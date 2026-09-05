"use client";

import { useId, useState } from "react";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { mensajeError } from "@/lib/formato";

/** Tarjeta para subir el PDF de una liquidación y disparar su procesamiento. */
export function SubirLiquidacion({ alSubir }: { alSubir: () => void }) {
  const idPeriodo = useId();
  const idArchivo = useId();
  const [periodo, setPeriodo] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<{ id: number; periodo: string; estado: string } | null>(null);

  async function alEnviar(e: React.FormEvent) {
    e.preventDefault();
    if (!archivo || !periodo) return;
    setError(null);
    setEnviando(true);
    try {
      const res = await api.subirLiquidacion(archivo, periodo);
      setResultado(res);
      toast.success(`Liquidación de ${res.periodo} en proceso`);
      alSubir();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="bg-white border border-borde-suave rounded-lg p-4">
      <form onSubmit={alEnviar} className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={idPeriodo}>Período (AAAA-MM)</Label>
          <Input
            id={idPeriodo}
            placeholder="2026-09"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={idArchivo}>Liquidación en PDF (hasta 30 MB)</Label>
          <input
            type="file"
            accept=".pdf,.txt"
            id={idArchivo}
            className="text-sm"
            onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
          />
        </div>
        <Button type="submit" disabled={enviando || !archivo || !periodo}>
          {enviando ? "Subiendo…" : "Subir y procesar"}
        </Button>
      </form>
      {resultado && (
        <p className="text-sm text-tinta-suave mt-2">
          La liquidación quedó procesando; en unos segundos vas a ver el resultado en la lista.
        </p>
      )}
      {error && (
        <p role="alert" className="text-[#B42318] text-sm mt-2">
          {error}
        </p>
      )}
    </div>
  );
}
