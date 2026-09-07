"use client";

import { useState } from "react";
import { ExternalLink, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { urlContenidoDocumento, type DocumentoInfo } from "@/lib/api";

/**
 * Visor de comprobantes bajo demanda: un botón "Ver comprobante" que abre el
 * PDF en un Dialog a pantalla casi completa (el iframe recién se carga al
 * abrirlo) más un link directo para verlo en una pestaña propia — más cómodo
 * en el celular.
 */
export function VisorDocumento({ documento }: { documento: DocumentoInfo }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
      <Dialog open={abierto} onOpenChange={setAbierto}>
        <DialogTrigger
          render={<Button type="button" variant="outline" size="lg" className="min-h-11" />}
        >
          <FileText />
          Ver comprobante: {documento.tipo}
        </DialogTrigger>
        <DialogContent className="h-[92dvh] w-[calc(100vw-1rem)] max-w-[calc(100vw-1rem)] sm:max-w-4xl grid-rows-[auto_minmax(0,1fr)] gap-2 p-3">
          <DialogTitle className="pr-10">Comprobante: {documento.tipo}</DialogTitle>
          {abierto && (
            <iframe
              src={urlContenidoDocumento(documento.id, { vista: true })}
              className="h-full w-full rounded-lg border border-borde-suave bg-white"
              title={`Documento ${documento.tipo}`}
            />
          )}
        </DialogContent>
      </Dialog>
      <a
        href={urlContenidoDocumento(documento.id, { vista: true })}
        target="_blank"
        rel="noreferrer"
        className="inline-flex min-h-11 items-center gap-1 text-sm text-institucional hover:underline"
        aria-label={`Abrir ${documento.tipo} en pestaña nueva`}
      >
        <ExternalLink className="h-4 w-4" aria-hidden />
        Abrir en pestaña nueva
      </a>
    </div>
  );
}
