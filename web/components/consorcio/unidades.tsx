"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { api, ApiError, type UnidadFila } from "@/lib/api";

/** Tabla de unidades funcionales con generación de códigos de acceso (se muestran una sola vez). */
export function TablaUnidades({
  unidades,
  alCambiar,
}: {
  unidades: UnidadFila[];
  alCambiar: () => void;
}) {
  const [cargando, setCargando] = useState<number | null>(null);
  const [codigo, setCodigo] = useState<{ uf: number; codigo: string } | null>(null);

  async function generar(uf: number) {
    setCargando(uf);
    try {
      const res = await api.generarCodigo(uf);
      setCodigo(res);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setCargando(null);
    }
  }

  async function copiar() {
    if (!codigo) return;
    try {
      await navigator.clipboard.writeText(codigo.codigo);
      toast.success("Copiado");
    } catch {
      toast.error("No se pudo copiar");
    }
  }

  function cerrar(abierto: boolean) {
    if (!abierto) {
      setCodigo(null);
      alCambiar();
    }
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>UF</TableHead>
            <TableHead>Piso</TableHead>
            <TableHead>Propietario</TableHead>
            <TableHead>Código</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {unidades.map((u) => (
            <TableRow key={u.uf}>
              <TableCell>{u.uf}</TableCell>
              <TableCell>{u.piso_depto}</TableCell>
              <TableCell>{u.propietario}</TableCell>
              <TableCell>
                {u.tiene_codigo ? (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-tinta-suave">emitido</span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={cargando === u.uf}
                      onClick={() => generar(u.uf)}
                    >
                      Regenerar
                    </Button>
                  </div>
                ) : (
                  <Button
                    size="sm"
                    disabled={cargando === u.uf}
                    onClick={() => generar(u.uf)}
                  >
                    Generar código
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={codigo !== null} onOpenChange={cerrar}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Código de acceso — UF {codigo?.uf}</DialogTitle>
          </DialogHeader>
          <p className="text-center font-mono text-3xl tracking-wider">{codigo?.codigo}</p>
          <p className="text-sm text-[#B42318]">
            Guardalo ahora: no se vuelve a mostrar.
          </p>
          <Button onClick={copiar}>Copiar</Button>
        </DialogContent>
      </Dialog>
    </>
  );
}
