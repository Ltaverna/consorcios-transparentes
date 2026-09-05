"use client";

import { useId, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";

/** Formulario de umbrales de reglas: uno por clave de `defaults`, siempre manda el dict completo (semántica PUT). */
export function FormularioUmbrales({
  umbrales,
  defaults,
  alGuardar,
}: {
  umbrales: Record<string, number>;
  defaults: Record<string, number>;
  alGuardar: () => void;
}) {
  const idBase = useId();
  const claves = Object.keys(defaults);
  const [valores, setValores] = useState<Record<string, string>>(() =>
    Object.fromEntries(claves.map((k) => [k, String(umbrales[k] ?? defaults[k])]))
  );
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function restaurarDefaults() {
    setValores(Object.fromEntries(claves.map((k) => [k, String(defaults[k])])));
  }

  async function alEnviar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setGuardando(true);
    try {
      const dictCompleto = Object.fromEntries(claves.map((k) => [k, Number(valores[k])]));
      await api.editarConsorcio({ umbrales: dictCompleto });
      toast.success("Umbrales guardados");
      alGuardar();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else toast.error("No se pudo conectar con el servidor");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <form onSubmit={alEnviar} className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {claves.map((clave) => {
          const id = `${idBase}-${clave}`;
          const modificado = Number(valores[clave]) !== defaults[clave];
          return (
            <div key={clave} className="flex flex-col gap-1.5">
              <Label htmlFor={id} className="font-mono text-sm">{clave}</Label>
              <Input
                id={id}
                type="number"
                value={valores[clave]}
                onChange={(e) => setValores((v) => ({ ...v, [clave]: e.target.value }))}
              />
              {modificado && (
                <span className="text-xs text-tinta-suave">Default: {defaults[clave]}</span>
              )}
            </div>
          );
        })}
      </div>
      <div className="flex gap-2">
        <Button type="submit" disabled={guardando}>
          {guardando ? "Guardando…" : "Guardar umbrales"}
        </Button>
        <Button type="button" variant="outline" onClick={restaurarDefaults} disabled={guardando}>
          Restaurar defaults
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-[#B42318] text-sm">
          {error}
        </p>
      )}
    </form>
  );
}
