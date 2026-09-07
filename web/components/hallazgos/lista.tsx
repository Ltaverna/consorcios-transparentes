"use client";

import { ChipSeveridad } from "@/components/severidad";
import { ChipEstado } from "@/components/estado-hallazgo";
import { cn } from "@/lib/utils";
import { moneda } from "@/lib/formato";
import type { HallazgoResumen } from "@/lib/api";

/**
 * Lista de hallazgos como tarjetas apiladas; cada una abre el drawer de detalle.
 * Si se pasa `alSeleccionar`, cada tarjeta lleva un checkbox para operar en lote.
 */
export function ListaHallazgos({
  filas,
  alAbrir,
  seleccionados,
  alSeleccionar,
}: {
  filas: HallazgoResumen[];
  alAbrir: (id: number) => void;
  seleccionados?: Set<number>;
  alSeleccionar?: (id: number, marcado: boolean) => void;
}) {
  if (filas.length === 0) {
    return <p className="text-tinta-suave text-sm py-8 text-center">No hay hallazgos con estos filtros.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      {filas.map((fila) => {
        const marcada = seleccionados?.has(fila.id) ?? false;
        return (
          <div
            key={fila.id}
            role="button"
            tabIndex={0}
            onClick={() => alAbrir(fila.id)}
            onKeyDown={(e) => {
              // Solo la tarjeta misma: el checkbox interior maneja sus propias teclas.
              if (e.target !== e.currentTarget) return;
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                alAbrir(fila.id);
              }
            }}
            className={cn(
              "bg-white border border-borde-suave rounded-lg p-3 cursor-pointer hover:border-[#123A5C] transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#123A5C]",
              marcada && "border-[#123A5C]"
            )}
          >
            <div className="flex items-start gap-3">
              {alSeleccionar && (
                <input
                  type="checkbox"
                  checked={marcada}
                  aria-label={`Seleccionar ${fila.titulo}`}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => alSeleccionar(fila.id, e.target.checked)}
                  className="mt-1 size-4 shrink-0 cursor-pointer accent-[#123A5C] outline-none focus-visible:ring-2 focus-visible:ring-[#123A5C]"
                />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <ChipSeveridad severidad={fila.severidad} />
                  <span className="font-semibold">{fila.titulo}</span>
                </div>
                <div className="text-sm text-tinta-suave flex items-center gap-2 mt-1">
                  <span className="tabular-nums">{moneda(fila.monto)}</span>
                  <span>·</span>
                  <ChipEstado estado={fila.estado} />
                  {fila.publicado && (
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded-full border border-[#0E7A4E] text-[#0E7A4E] bg-white">
                      publicado
                    </span>
                  )}
                  <span>·</span>
                  <span>{fila.periodo}</span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
