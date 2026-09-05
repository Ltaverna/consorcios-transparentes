"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FormularioUmbrales } from "@/components/consorcio/umbrales";
import { TablaUnidades } from "@/components/consorcio/unidades";
import { mensajeError } from "@/lib/formato";
import { api, type ConsorcioInfo, type UnidadFila } from "@/lib/api";

const CAMPOS_DATOS: { clave: keyof Omit<ConsorcioInfo, "umbrales" | "umbrales_default">; etiqueta: string }[] = [
  { clave: "nombre", etiqueta: "Nombre" },
  { clave: "direccion", etiqueta: "Dirección" },
  { clave: "cuit", etiqueta: "CUIT" },
  { clave: "admin_nombre", etiqueta: "Administrador" },
  { clave: "admin_cuit", etiqueta: "CUIT del administrador" },
  { clave: "marca", etiqueta: "Marca" },
];

export default function ConsorcioPage() {
  const [consorcio, setConsorcio] = useState<ConsorcioInfo | null>(null);
  const [unidades, setUnidades] = useState<UnidadFila[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [datos, setDatos] = useState<Record<string, string>>({});
  const [guardandoDatos, setGuardandoDatos] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const [info, filas] = await Promise.all([api.verConsorcio(), api.listarUnidades()]);
      setConsorcio(info);
      setUnidades(filas);
      setDatos(
        Object.fromEntries(CAMPOS_DATOS.map(({ clave }) => [clave, String(info[clave] ?? "")]))
      );
    } catch (err) {
      const mensaje = mensajeError(err);
      toast.error(mensaje);
      setError(mensaje);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  async function guardarDatos(e: React.FormEvent) {
    e.preventDefault();
    setGuardandoDatos(true);
    try {
      await api.editarConsorcio({ ...datos });
      toast.success("Datos guardados");
      cargar();
    } catch (err) {
      toast.error(mensajeError(err));
    } finally {
      setGuardandoDatos(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-titulos text-xl font-bold">Consorcio</h1>

      {cargando ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-tinta-suave">{error}</p>
            <Button variant="outline" onClick={cargar}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : consorcio ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Datos del consorcio</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={guardarDatos} className="flex flex-col gap-3">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {CAMPOS_DATOS.map(({ clave, etiqueta }) => (
                    <div key={clave} className="flex flex-col gap-1.5">
                      <Label htmlFor={`consorcio-${clave}`}>{etiqueta}</Label>
                      <Input
                        id={`consorcio-${clave}`}
                        value={datos[clave] ?? ""}
                        onChange={(e) => setDatos((d) => ({ ...d, [clave]: e.target.value }))}
                      />
                    </div>
                  ))}
                </div>
                <Button type="submit" disabled={guardandoDatos} className="self-start">
                  {guardandoDatos ? "Guardando…" : "Guardar datos"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Umbrales de las reglas</CardTitle>
            </CardHeader>
            <CardContent>
              <FormularioUmbrales
                umbrales={consorcio.umbrales}
                defaults={consorcio.umbrales_default}
                alGuardar={cargar}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Unidades</CardTitle>
            </CardHeader>
            <CardContent>
              <TablaUnidades unidades={unidades} alCambiar={cargar} />
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
