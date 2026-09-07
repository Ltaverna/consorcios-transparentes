"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ChipSeveridad } from "@/components/severidad";
import { ChipEstadoGasto } from "@/components/estado-gasto";
import { api, ApiError, urlInforme, urlContenidoDocumento, type MiUnidad, type HallazgoDetalle, type DocumentoInfo, type IndiceTransparencia } from "@/lib/api";
import { documentosDelHallazgo } from "@/components/hallazgos/documentos-de";
import { COMPONENTES_INDICE, cuentaPenalizacion, moneda, mensajeError, puntosIndice } from "@/lib/formato";

interface HallazgoConDocs {
  detalle: HallazgoDetalle;
  documentos: DocumentoInfo[];
}

export default function PaginaMiUnidad() {
  const [datos, setDatos] = useState<MiUnidad | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hallazgos, setHallazgos] = useState<HallazgoConDocs[]>([]);
  const [indice, setIndice] = useState<IndiceTransparencia | null>(null);

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

  useEffect(() => {
    (async () => {
      try {
        const resumenes = await api.listarHallazgos();
        if (resumenes.length === 0) return;
        const resultado: HallazgoConDocs[] = [];
        for (const r of resumenes) {
          const [detalle, documentosTodos] = await Promise.all([
            api.detalleHallazgo(r.id),
            api.listarDocumentos(r.liquidacion_id),
          ]);
          const documentos = documentosDelHallazgo(detalle, documentosTodos);
          resultado.push({ detalle, documentos });
        }
        setHallazgos(resultado);
      } catch {
        // error no crítico: no rompe el resto de la página
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.indiceTransparencia();
        setIndice(res);
      } catch {
        // error no crítico: la card se oculta en silencio, el resto de mi-unidad sigue funcionando
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
                    <div className={`text-lg font-semibold tabular-nums ${datos.estado_cuenta.deuda > 0 ? "text-[#B42318]" : "text-exito"}`}>
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

          <div className="flex items-center justify-between">
            <a
              href={urlInforme(datos.periodo, "xlsx")}
              className="inline-flex h-8 items-center justify-center gap-1.5 rounded-lg bg-primary px-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/80"
            >
              Descargar Excel
            </a>
            <a
              href="/reglamento"
              className="text-sm text-tinta-suave underline underline-offset-2 hover:text-tinta"
            >
              Reglamento de copropiedad
            </a>
          </div>

          {indice && (
            <Card>
              <CardHeader>
                <CardTitle>Transparencia</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                {indice.periodos.length === 0 ? (
                  <p className="text-sm text-tinta-suave">Todavía no hay períodos publicados.</p>
                ) : (
                  <>
                    <div className="flex items-baseline gap-2">
                      <span className="text-4xl font-bold tabular-nums">{indice.indice}</span>
                      <span className="text-lg text-tinta-suave">/ 100</span>
                    </div>
                    <p className="text-xs text-tinta-suave">
                      % del dinero con trazabilidad documental completa sobre las liquidaciones publicadas
                    </p>

                    <div className="flex flex-col gap-2">
                      {[
                        { label: "Trazable", pct: indice.totales.pct_trazable, importe: indice.totales.dinero_verificado },
                        { label: "Con factura", pct: indice.totales.pct_con_factura, importe: indice.totales.dinero_con_factura },
                        { label: "Pagos respaldados", pct: indice.totales.pct_pago_respaldado, importe: indice.totales.dinero_pago_respaldado },
                      ].map(({ label, pct, importe }) => (
                        <div key={label} className="flex flex-col gap-1">
                          <div className="flex justify-between text-xs">
                            <span>{label}</span>
                            <span className="tabular-nums">{Math.round(pct * 100)}% · {moneda(importe)}</span>
                          </div>
                          <div className="h-2 rounded-full bg-borde-suave overflow-hidden">
                            <div
                              className="h-full bg-institucional rounded-full"
                              style={{ width: `${Math.round(pct * 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    {indice.totales.componentes && (
                      <div className="flex flex-col gap-1">
                        <span className="text-xs font-semibold text-tinta-suave uppercase tracking-wide">Desglose del índice</span>
                        {COMPONENTES_INDICE.filter(({ clave }) => indice.totales.componentes![clave]).map(({ clave, etiqueta }) => {
                          const c = indice.totales.componentes![clave];
                          return (
                            <div key={clave} className="flex justify-between text-xs">
                              <span>{etiqueta}</span>
                              <span className="tabular-nums">{puntosIndice(c.puntos)} pts</span>
                            </div>
                          );
                        })}
                        {indice.totales.penalizacion && indice.totales.penalizacion.criticos_abiertos > 0 && (
                          <div className="flex justify-between text-xs">
                            <span>Penalización: {cuentaPenalizacion(indice.totales.penalizacion)}</span>
                            <span className="tabular-nums">−{indice.totales.penalizacion.puntos} pts</span>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="flex flex-col gap-1">
                      <span className="text-xs font-semibold text-tinta-suave uppercase tracking-wide">Estados de los gastos</span>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(indice.totales.gastos_por_estado)
                          .filter(([, v]) => v.cantidad > 0)
                          .map(([estado, v]) => (
                            <span key={estado} className="flex items-center gap-1 text-sm">
                              <ChipEstadoGasto estado={estado} />
                              <span className="tabular-nums text-tinta-suave">{v.cantidad}</span>
                            </span>
                          ))}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          <iframe
            src={urlInforme(datos.periodo, "html")}
            className="w-full min-h-[70vh] bg-white border border-borde-suave rounded-lg"
            title="Informe de expensas"
          />

          {hallazgos.length > 0 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-titulos text-lg font-bold">Hallazgos publicados</h2>
              {hallazgos.map(({ detalle, documentos }) => (
                <Card key={detalle.id}>
                  <CardContent className="flex flex-col gap-3 py-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <ChipSeveridad severidad={detalle.severidad} />
                      <span className="font-semibold">{detalle.titulo}</span>
                    </div>
                    <p className="text-sm tabular-nums text-tinta-suave">{moneda(detalle.monto)}</p>
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-semibold">Evidencia</span>
                      <p className="text-sm leading-relaxed">{String(detalle.evidencia)}</p>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-semibold">Qué pedir</span>
                      <p className="text-sm leading-relaxed">{detalle.recomendacion}</p>
                    </div>
                    {detalle.respuesta_admin && (
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-semibold">Respuesta de la administración</span>
                        <p className="text-sm leading-relaxed">{detalle.respuesta_admin}</p>
                      </div>
                    )}
                    {documentos.length > 0 && (
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-semibold">Documentos</span>
                        <div className="grid gap-3 md:grid-cols-2">
                          {documentos.map((d) => (
                            <div key={d.id} className="flex flex-col gap-1">
                              <a
                                href={urlContenidoDocumento(d.id)}
                                target="_blank"
                                rel="noreferrer"
                                className="text-institucional hover:underline text-sm inline-flex items-center gap-1"
                              >
                                {d.tipo}
                              </a>
                              <iframe
                                src={urlContenidoDocumento(d.id, { vista: true })}
                                className="w-full h-64 border rounded"
                                title={`Documento ${d.tipo}`}
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
