type Tono = "normal" | "critico" | "exito";

const COLOR_POR_TONO: Record<Tono, string> = {
  normal: "text-tinta",
  critico: "text-[#B42318]",
  exito: "text-exito",
};

/** Tarjeta que muestra un indicador clave (KPI) con etiqueta y valor. */
export function Kpi({
  etiqueta,
  valor,
  tono = "normal",
}: {
  etiqueta: string;
  valor: string;
  tono?: Tono;
}) {
  return (
    <div className="bg-white border border-borde-suave rounded-lg p-4">
      <div className="text-xs uppercase tracking-wide text-tinta-suave">
        {etiqueta}
      </div>
      <div className={`font-titulos text-2xl font-bold ${COLOR_POR_TONO[tono]}`}>
        {valor}
      </div>
    </div>
  );
}
