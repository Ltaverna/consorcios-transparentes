import { CHIP_BASE } from "@/components/chip-base";

type EstadoHallazgo = "pendiente" | "preguntado" | "respondido" | "descartado" | "cerrado" | (string & {});

const CLASES_POR_ESTADO: Record<string, string> = {
  pendiente: "bg-[#123A5C] text-white",
  preguntado: "bg-[#FEF0C7] text-[#93540B]",
  respondido: "bg-[#DBEAFE] text-[#1D4ED8]",
  descartado: "bg-[#E2E8F0] text-[#475569]",
  cerrado: "bg-[#DCFCE7] text-[#0E7A4E]",
};

const CLASES_POR_DEFECTO = "bg-[#E2E8F0] text-[#475569]";

/** Chip visual que indica el estado de un hallazgo dentro de su ciclo de vida. */
export function ChipEstado({ estado }: { estado: EstadoHallazgo }) {
  const clases = CLASES_POR_ESTADO[estado] ?? CLASES_POR_DEFECTO;

  return <span className={`${CHIP_BASE} ${clases}`}>{estado}</span>;
}
