"use client";

import { useId, useState } from "react";
import { FileText } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ChipSeveridad } from "@/components/severidad";
import { ChipEstado } from "@/components/estado-hallazgo";
import { moneda, fecha } from "@/lib/formato";
import {
  api,
  ApiError,
  urlContenidoDocumento,
  type DocumentoInfo,
  type HallazgoDetalle,
} from "@/lib/api";

const ESTADOS = ["pendiente", "preguntado", "respondido", "descartado", "cerrado"] as const;

function mensajeError(err: unknown): string {
  return err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor";
}

function SelectorEstado({
  hallazgoId,
  estadoActual,
  alCambiar,
}: {
  hallazgoId: number;
  estadoActual: string;
  alCambiar: () => void;
}) {
  const idNota = useId();
  const [elegido, setElegido] = useState<string | null>(null);
  const [nota, setNota] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function confirmar() {
    if (!elegido) return;
    setEnviando(true);
    try {
      await api.cambiarEstado(hallazgoId, elegido, nota);
      toast.success("Se actualizó el estado del hallazgo");
      setElegido(null);
      setNota("");
      alCambiar();
    } catch (err) {
      toast.error(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {ESTADOS.map((estado) => (
          <Button
            key={estado}
            type="button"
            variant={estado === estadoActual ? "default" : "outline"}
            size="sm"
            className={estado === estadoActual ? "bg-[#123A5C] text-white" : ""}
            onClick={() => setElegido(estado === elegido ? null : estado)}
          >
            {estado}
          </Button>
        ))}
      </div>
      {elegido && (
        <div className="flex flex-col gap-2 border border-borde-suave rounded-lg p-3">
          <Label htmlFor={idNota}>Nota (opcional)</Label>
          <Textarea id={idNota} value={nota} onChange={(e) => setNota(e.target.value)} />
          <Button type="button" onClick={confirmar} disabled={enviando}>
            {enviando ? "Confirmando…" : "Confirmar cambio"}
          </Button>
        </div>
      )}
    </div>
  );
}

function TogglePublicar({
  hallazgoId,
  publicado,
  alCambiar,
}: {
  hallazgoId: number;
  publicado: boolean;
  alCambiar: () => void;
}) {
  const idSwitch = useId();
  const [enviando, setEnviando] = useState(false);

  async function alClickear() {
    setEnviando(true);
    try {
      const res = await api.publicarHallazgo(hallazgoId, !publicado);
      toast.success(res.publicado ? "Se marcó para publicar" : "Se sacó de la publicación");
      alCambiar();
    } catch (err) {
      toast.error(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Switch
        id={idSwitch}
        aria-label="Publicar en el informe"
        checked={publicado}
        disabled={enviando}
        onCheckedChange={alClickear}
      />
      <Label htmlFor={idSwitch}>Publicar en el informe</Label>
    </div>
  );
}

function RespuestaAdmin({
  hallazgoId,
  respuestaInicial,
}: {
  hallazgoId: number;
  respuestaInicial: string;
}) {
  const idRespuesta = useId();
  const [texto, setTexto] = useState(respuestaInicial);
  const [guardando, setGuardando] = useState(false);

  async function guardar() {
    setGuardando(true);
    try {
      await api.registrarRespuesta(hallazgoId, texto);
      toast.success("Se guardó la respuesta");
    } catch (err) {
      toast.error(mensajeError(err));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={idRespuesta}>Respuesta de la administración</Label>
      <Textarea id={idRespuesta} value={texto} onChange={(e) => setTexto(e.target.value)} />
      <Button type="button" onClick={guardar} disabled={guardando} className="self-start">
        {guardando ? "Guardando…" : "Guardar respuesta"}
      </Button>
    </div>
  );
}

/**
 * Cuerpo compartido entre el drawer de triage y la página de detalle: muestra
 * la evidencia, la recomendación, los documentos, el cambio de estado, el
 * toggle de publicación, la respuesta de la administración y el historial.
 */
export function FichaHallazgo({
  detalle,
  documentos,
  alCambiar,
  conVisor = true,
}: {
  detalle: HallazgoDetalle;
  documentos: DocumentoInfo[];
  alCambiar: () => void;
  conVisor?: boolean;
}) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 flex-wrap">
          <ChipSeveridad severidad={detalle.severidad} />
          <ChipEstado estado={detalle.estado} />
          <h2 className="font-titulos text-lg font-bold">{detalle.titulo}</h2>
        </div>
        <p className="text-sm text-tinta-suave">{moneda(detalle.monto)}</p>
      </div>

      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold">Evidencia</h3>
        <p className="text-sm leading-relaxed">{String(detalle.evidencia)}</p>
      </div>

      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold">Qué pedir</h3>
        <p className="text-sm leading-relaxed">{detalle.recomendacion}</p>
      </div>

      {documentos.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold">Documentos</h3>
          <div className="flex flex-col gap-2">
            {documentos.map((d) => (
              <div key={d.id} className="flex flex-col gap-1">
                <a
                  href={urlContenidoDocumento(d.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-institucional hover:underline inline-flex items-center gap-1 text-sm"
                >
                  <FileText className="w-4 h-4" />
                  {d.tipo}
                </a>
                {conVisor && (
                  <iframe
                    src={urlContenidoDocumento(d.id)}
                    className="w-full h-64 border rounded"
                    title={`Documento ${d.tipo}`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <SelectorEstado hallazgoId={detalle.id} estadoActual={detalle.estado} alCambiar={alCambiar} />

      <TogglePublicar hallazgoId={detalle.id} publicado={detalle.publicado} alCambiar={alCambiar} />

      <RespuestaAdmin hallazgoId={detalle.id} respuestaInicial={detalle.respuesta_admin} />

      {detalle.eventos.length > 0 && (
        <div className="flex flex-col gap-1">
          <h3 className="text-sm font-semibold">Historial</h3>
          <ul className="flex flex-col gap-1 text-sm text-tinta-suave">
            {detalle.eventos.map((e, i) => (
              <li key={i}>
                {fecha(e.ts)} · {e.usuario} · {e.de || "—"} → {e.a}
                {e.nota && <> — {e.nota}</>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
