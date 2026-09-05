import { CHIP_BASE } from "@/components/chip-base";

type Severidad = "CRÍTICO" | "ALTO" | "MEDIO" | "BAJO" | (string & {});

const CLASES_POR_SEVERIDAD: Record<string, string> = {
  CRÍTICO: "bg-[#FEE4E2] text-[#B42318]",
  ALTO: "bg-[#FEF0C7] text-[#93540B]",
  MEDIO: "bg-[#DBEAFE] text-[#1D4ED8]",
  BAJO: "bg-[#E2E8F0] text-[#475569]",
};

const CLASES_POR_DEFECTO = CLASES_POR_SEVERIDAD.BAJO;

/** Chip visual que indica la severidad de un hallazgo. */
export function ChipSeveridad({ severidad }: { severidad: Severidad }) {
  const clases = CLASES_POR_SEVERIDAD[severidad] ?? CLASES_POR_DEFECTO;

  return <span className={`${CHIP_BASE} ${clases}`}>{severidad}</span>;
}
