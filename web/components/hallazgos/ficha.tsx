"use client";

import { useId, useState } from "react";
import { useRol } from "@/components/rol-context";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ChipSeveridad } from "@/components/severidad";
import { ChipEstado } from "@/components/estado-hallazgo";
import { VisorDocumento } from "@/components/hallazgos/visor-documento";
import { moneda, fecha, mensajeError } from "@/lib/formato";
import { api, type DocumentoInfo, type HallazgoDetalle } from "@/lib/api";

const ESTADOS = ["pendiente", "preguntado", "respondido", "descartado", "cerrado"] as const;

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
      toast.success("Se actualizó el estado del hallazgo", {
        description: "Si el informe del período ya estaba publicado, volvé a publicarlo para que refleje este cambio.",
      });
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
      <h3 className="text-sm font-semibold">Estado</h3>
      <div className="flex flex-wrap gap-2">
        {ESTADOS.map((estado) => {
          const esActual = estado === estadoActual;
          const esElegido = estado === elegido;
          return (
            <Button
              key={estado}
              type="button"
              variant={esActual ? "default" : "outline"}
              size="sm"
              aria-pressed={esElegido}
              className={cn(
                "min-h-9 px-3.5",
                esActual && "bg-[#123A5C] text-white",
                esElegido && "ring-2 ring-[#123A5C] ring-offset-1 border-[#123A5C] bg-[#E8EFF6] text-[#123A5C]"
              )}
              onClick={() => setElegido(estado === elegido ? null : estado)}
            >
              {estado}
            </Button>
          );
        })}
      </div>
      {elegido && (
        <div className="flex flex-col gap-2 border border-borde-suave rounded-lg p-3">
          <p className="text-sm">
            Cambiar a <strong>{elegido}</strong>
          </p>
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
      toast.success(res.publicado ? "Se marcó para publicar" : "Se sacó de la publicación", {
        description: "Si el informe del período ya estaba publicado, volvé a publicarlo para que refleje este cambio.",
      });
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
 * la evidencia, la recomendación, los documentos (con visor bajo demanda), el
 * cambio de estado, el toggle de publicación, la respuesta de la
 * administración y el historial.
 */
export function FichaHallazgo({
  detalle,
  documentos,
  alCambiar,
}: {
  detalle: HallazgoDetalle;
  documentos: DocumentoInfo[];
  alCambiar: () => void;
}) {
  const rol = useRol();
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
              <VisorDocumento key={d.id} documento={d} />
            ))}
          </div>
        </div>
      )}

      {rol === "auditor" ? (
        <>
          <SelectorEstado hallazgoId={detalle.id} estadoActual={detalle.estado} alCambiar={alCambiar} />
          <TogglePublicar hallazgoId={detalle.id} publicado={detalle.publicado} alCambiar={alCambiar} />
          <RespuestaAdmin hallazgoId={detalle.id} respuestaInicial={detalle.respuesta_admin} />
        </>
      ) : (
        detalle.respuesta_admin && (
          <div className="flex flex-col gap-1">
            <h3 className="text-sm font-semibold">Respuesta de la administración</h3>
            <p className="text-sm leading-relaxed">{detalle.respuesta_admin}</p>
          </div>
        )
      )}

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
