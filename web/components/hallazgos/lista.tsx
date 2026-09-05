"use client";

import { ChipSeveridad } from "@/components/severidad";
import { ChipEstado } from "@/components/estado-hallazgo";
import { moneda } from "@/lib/formato";
import type { HallazgoResumen } from "@/lib/api";

/** Lista de hallazgos como tarjetas apiladas; cada una abre el drawer de detalle. */
export function ListaHallazgos({
  filas,
  alAbrir,
}: {
  filas: HallazgoResumen[];
  alAbrir: (id: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {filas.map((fila) => (
        <div
          key={fila.id}
          role="button"
          tabIndex={0}
          onClick={() => alAbrir(fila.id)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              alAbrir(fila.id);
            }
          }}
          className="bg-white border border-borde-suave rounded-lg p-3 cursor-pointer hover:border-[#123A5C] transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#123A5C]"
        >
          <div className="flex items-center gap-2">
            <ChipSeveridad severidad={fila.severidad} />
            <span className="font-semibold">{fila.titulo}</span>
          </div>
          <div className="text-sm text-tinta-suave flex items-center gap-2 mt-1">
            <span className="tabular-nums">{moneda(fila.monto)}</span>
            <span>·</span>
            <ChipEstado estado={fila.estado} />
            {fila.publicado && (
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#DCFCE7] text-[#0E7A4E]">
                publicado
              </span>
            )}
            <span>·</span>
            <span>{fila.periodo}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
