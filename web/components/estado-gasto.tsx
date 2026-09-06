import { CHIP_BASE } from "@/components/chip-base";

export const ETIQUETAS_ESTADO_GASTO: Record<string, string> = {
  verificado: "✅ Verificado",
  requiere_explicacion: "🟡 Requiere explicación",
  anomalia: "🟠 Anomalía",
  inconsistencia: "🔴 Inconsistencia",
  sin_informacion: "⚪ Sin información",
};

const CLASES: Record<string, string> = {
  verificado: "bg-[#DCFCE7] text-[#0E7A4E]",
  requiere_explicacion: "bg-[#FEF0C7] text-[#93540B]",
  anomalia: "bg-[#FFEAD5] text-[#B93815]",
  inconsistencia: "bg-[#FEE4E2] text-[#B42318]",
  sin_informacion: "bg-[#E2E8F0] text-[#475569]",
};

/** Chip visual del estado de trazabilidad de un gasto. */
export function ChipEstadoGasto({ estado }: { estado: string }) {
  return (
    <span className={`${CHIP_BASE} ${CLASES[estado] ?? CLASES.sin_informacion}`}>
      {ETIQUETAS_ESTADO_GASTO[estado] ?? estado}
    </span>
  );
}
