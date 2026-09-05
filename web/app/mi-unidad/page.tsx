"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError, urlInforme, type MiUnidad } from "@/lib/api";
import { moneda, mensajeError } from "@/lib/formato";

export default function PaginaMiUnidad() {
  const [datos, setDatos] = useState<MiUnidad | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.miUnidad();
        setDatos(res);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setError(err.detail);
        } else {
          const mensaje = mensajeError(err);
          toast.error(mensaje);
          setError(mensaje);
        }
      } finally {
        setCargando(false);
      }
    })();
  }, []);

  async function alSalir() {
    try {
      await api.salir();
    } catch {
      // igual redirigimos: la sesión del lado del servidor puede haber vencido
    } finally {
      window.location.href = "/entrar";
    }
  }

  return (
    <div className="min-h-screen bg-fondo">
      <header className="bg-[#123A5C] text-white px-6 py-3 flex justify-between items-center">
        <span className="font-titulos font-bold">Consorcio Transparente</span>
        <Button variant="secondary" size="sm" onClick={alSalir}>
          Salir
        </Button>
      </header>

      {cargando ? (
        <div className="max-w-4xl mx-auto p-6 space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-10 w-40" />
          <Skeleton className="h-[70vh] w-full" />
        </div>
      ) : error ? (
        <div className="flex items-center justify-center p-6">
          <Card className="max-w-md w-full">
            <CardContent className="text-center text-tinta-suave py-6">{error}</CardContent>
          </Card>
        </div>
      ) : datos ? (
        <div className="max-w-4xl mx-auto p-6 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-baseline justify-between">
                <span>
                  Tu unidad · {datos.estado_cuenta ? `${datos.estado_cuenta.piso_depto} (UF ${datos.uf})` : `UF ${datos.uf}`}
                </span>
                <span className="text-sm font-normal text-tinta-suave">Período {datos.periodo}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {datos.estado_cuenta ? (
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-xs text-tinta-suave">Expensas del mes</div>
                    <div className="text-lg font-semibold tabular-nums">{moneda(datos.estado_cuenta.total_mes)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-tinta-suave">A pagar</div>
                    <div className="text-lg font-semibold tabular-nums">{moneda(datos.estado_cuenta.a_pagar)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-tinta-suave">Deuda</div>
                    <div className={`text-lg font-semibold tabular-nums ${datos.estado_cuenta.deuda > 0 ? "text-[#B42318]" : "text-green-600"}`}>
                      {datos.estado_cuenta.deuda > 0 ? moneda(datos.estado_cuenta.deuda) : "Sin deuda"}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-tinta-suave">
                  No encontramos el detalle de tu unidad en este período.
                </p>
              )}
            </CardContent>
          </Card>

          <a
            href={urlInforme(datos.periodo, "xlsx")}
            className="inline-flex h-8 items-center justify-center gap-1.5 rounded-lg bg-primary px-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/80"
          >
            Descargar Excel
          </a>

          <iframe
            src={urlInforme(datos.periodo, "html")}
            className="w-full min-h-[70vh] bg-white border border-borde-suave rounded-lg"
            title="Informe de expensas"
          />
        </div>
      ) : null}
    </div>
  );
}
