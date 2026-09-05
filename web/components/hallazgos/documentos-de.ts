import type { DocumentoInfo, HallazgoDetalle } from "@/lib/api";

/**
 * Documentos que respaldan un hallazgo. Solo tiene sentido para hallazgos de
 * origen "comprobantes", donde `refs` son ids de documento (`gasto_n`). Para
 * hallazgos de origen "liquidacion" las refs son ambiguas (pueden ser números
 * de UF u otra cosa), así que no se listan documentos.
 */
export function documentosDelHallazgo(
  detalle: HallazgoDetalle,
  documentos: DocumentoInfo[]
): DocumentoInfo[] {
  if (detalle.origen !== "comprobantes") return [];
  return documentos.filter((d) => detalle.refs.includes(String(d.gasto_n)));
}
