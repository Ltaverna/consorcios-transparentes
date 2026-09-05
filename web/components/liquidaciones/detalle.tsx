"use client";

import { FileText } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Kpi } from "@/components/kpi";
import { moneda } from "@/lib/formato";
import { urlContenidoDocumento, type DocumentoInfo, type LiquidacionDetalle } from "@/lib/api";

/** Muestra el cuadre, los totales por categoría y el detalle de gastos de una liquidación. */
export function DetalleLiquidacion({
  detalle,
  documentos,
}: {
  detalle: LiquidacionDetalle;
  documentos: DocumentoInfo[];
}) {
  const { cuadra, checks_ok, checks_mal, checks, sistema, totales_categoria, gastos } = detalle;
  const checksFallidos = checks.filter((c) => !c.ok);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-3 gap-4">
        <Kpi
          etiqueta="Cuadre"
          valor={`${checks_ok}/${checks_ok + checks_mal}`}
          tono={cuadra ? "exito" : "critico"}
        />
        <Kpi etiqueta="Gastos" valor={String(gastos.length)} />
        <Kpi etiqueta="Sistema" valor={sistema || "—"} />
      </div>

      {!cuadra && (
        <div className="bg-[#FEE4E2] text-[#B42318] rounded-lg p-4 font-semibold flex flex-col gap-3">
          <p>Esta liquidación no cuadra — no se puede publicar</p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Check</TableHead>
                <TableHead>Esperado</TableHead>
                <TableHead>Obtenido</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {checksFallidos.map((c) => (
                <TableRow key={c.nombre}>
                  <TableCell>{c.nombre}</TableCell>
                  <TableCell>{moneda(Number(c.esperado))}</TableCell>
                  <TableCell>{moneda(Number(c.obtenido))}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <div>
        <h2 className="font-titulos text-lg font-bold mb-2">Totales por categoría</h2>
        <Table>
          <TableBody>
            {Object.entries(totales_categoria).map(([categoria, importe]) => (
              <TableRow key={categoria}>
                <TableCell>{categoria}</TableCell>
                <TableCell className="text-right tabular-nums">{moneda(importe)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div>
        <h2 className="font-titulos text-lg font-bold mb-2">Gastos</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>N</TableHead>
              <TableHead>Categoría</TableHead>
              <TableHead>Proveedor</TableHead>
              <TableHead>Concepto</TableHead>
              <TableHead className="text-right">Importe</TableHead>
              <TableHead>Factura</TableHead>
              <TableHead>Forma de pago</TableHead>
              <TableHead>Comprobantes</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {gastos.map((g) => {
              const docsGasto = documentos.filter((d) => d.gasto_n === g.n);
              const formas = Array.from(new Set(g.pagos.map((p) => p.forma)));
              return (
                <TableRow key={g.n}>
                  <TableCell>{g.n}</TableCell>
                  <TableCell>{g.categoria}</TableCell>
                  <TableCell>{g.proveedor}</TableCell>
                  <TableCell className="max-w-[28rem] truncate" title={g.concepto}>
                    {g.concepto}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{moneda(g.importe)}</TableCell>
                  <TableCell>{g.factura_nro ?? "—"}</TableCell>
                  <TableCell>{formas.join(", ")}</TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      {docsGasto.map((d) => (
                        <a
                          key={d.id}
                          href={urlContenidoDocumento(d.id)}
                          target="_blank"
                          rel="noreferrer"
                          className="text-institucional hover:underline inline-flex items-center gap-1"
                        >
                          <FileText className="w-4 h-4" />
                          comprobante
                        </a>
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
