"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRol } from "@/components/rol-context";
import { SubirComprobantes } from "@/components/liquidaciones/subir-comprobantes";
import { CHIP_BASE } from "@/components/chip-base";
import type { LiquidacionResumen } from "@/lib/api";

const BASE_CHIP = `${CHIP_BASE} inline-flex items-center gap-1`;

function ChipEstadoLiquidacion({ estado }: { estado: string }) {
  switch (estado) {
    case "publicada":
      return <span className={`${BASE_CHIP} bg-[#DCFCE7] text-[#0E7A4E]`}>publicada</span>;
    case "procesada":
      return <span className={`${BASE_CHIP} bg-[#DBEAFE] text-[#1D4ED8]`}>procesada</span>;
    case "procesando":
      return (
        <span className={`${BASE_CHIP} bg-[#E2E8F0] text-[#475569]`}>
          <Loader2 className="size-3 animate-spin" />
          procesando
        </span>
      );
    case "no_cuadra":
      return <span className={`${BASE_CHIP} bg-[#FEE4E2] text-[#B42318]`}>no cuadra</span>;
    case "error":
      return <span className={`${BASE_CHIP} bg-[#FEE4E2] text-[#B42318]`}>error</span>;
    default:
      return <span className={`${BASE_CHIP} bg-[#E2E8F0] text-[#475569]`}>{estado}</span>;
  }
}

/** Tabla de liquidaciones con su estado y las acciones disponibles según ese estado. */
export function ListaLiquidaciones({
  filas,
  alCambiar,
}: {
  filas: LiquidacionResumen[];
  alCambiar: () => void;
}) {
  const rol = useRol();
  if (filas.length === 0) {
    return (
      <p className="text-tinta-suave text-sm py-8 text-center">
        {rol === "auditor"
          ? "Todavía no hay liquidaciones — subí la primera."
          : "Todavía no hay liquidaciones."}
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Período</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead>Sistema</TableHead>
          <TableHead>Acciones</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {filas.map((fila) => (
          <TableRow key={fila.id}>
            <TableCell>{fila.periodo}</TableCell>
            <TableCell>
              <ChipEstadoLiquidacion estado={fila.estado} />
              {fila.estado === "error" && fila.error && (
                <p className="text-tinta-suave text-sm">{fila.error}</p>
              )}
            </TableCell>
            <TableCell>{fila.sistema}</TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <Link href={`/panel/liquidaciones/${fila.id}`} className="text-sm underline">
                  Ver detalle
                </Link>
                {rol === "auditor" && (fila.estado === "procesada" || fila.estado === "publicada") && (
                  <SubirComprobantes
                    liquidacionId={fila.id}
                    periodo={fila.periodo}
                    alCambiar={alCambiar}
                  />
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
