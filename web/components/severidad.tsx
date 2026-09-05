const BASE = "text-[11px] font-bold px-2 py-0.5 rounded-full";

const CLASES_POR_SEVERIDAD: Record<string, string> = {
  CRÍTICO: "bg-[#FEE4E2] text-[#B42318]",
  ALTO: "bg-[#FEF0C7] text-[#93540B]",
  MEDIO: "bg-[#DBEAFE] text-[#1D4ED8]",
  BAJO: "bg-[#E2E8F0] text-[#475569]",
};

const CLASES_POR_DEFECTO = CLASES_POR_SEVERIDAD.BAJO;

/** Chip visual que indica la severidad de un hallazgo. */
export function ChipSeveridad({ severidad }: { severidad: string }) {
  const clases = CLASES_POR_SEVERIDAD[severidad] ?? CLASES_POR_DEFECTO;

  return <span className={`${BASE} ${clases}`}>{severidad}</span>;
}
