"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useRol } from "@/components/rol-context";
import { api, urlReglamento } from "@/lib/api";
import { mensajeError } from "@/lib/formato";

export default function PaginaReglamento() {
  const rol = useRol();
  const [estado, setEstado] = useState<{ pdf: boolean; transcripcion: boolean } | null>(null);
  const [texto, setTexto] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const est = await api.estadoReglamento();
      setEstado(est);
      if (est.transcripcion) setTexto(await api.textoReglamento());
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- patrón de carga establecido; ver plan Task 12
    cargar();
  }, [cargar]);

  const vacio = estado && !estado.pdf && !estado.transcripcion;

  return (
    <div className="min-h-screen bg-fondo">
      <header className="bg-[#123A5C] text-white px-6 py-3 flex justify-between items-center">
        <span className="font-titulos font-bold">Consorcio Transparente</span>
      </header>

      <div className="max-w-3xl mx-auto p-6 space-y-4">
        {cargando ? (
          <>
            <Skeleton className="h-10 w-48" />
            <Skeleton className="h-[60vh] w-full" />
          </>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-tinta-suave">{error}</p>
              <Button variant="outline" onClick={cargar}>
                Reintentar
              </Button>
            </CardContent>
          </Card>
        ) : vacio ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-tinta-suave">El reglamento todavía no está cargado.</p>
              {rol !== "propietario" && (
                <Link href="/panel/consorcio" className="text-sm underline underline-offset-2 hover:opacity-80">
                  Subirlo desde Consorcio
                </Link>
              )}
            </CardContent>
          </Card>
        ) : estado ? (
          <>
            {estado.pdf && (
              <a
                href={urlReglamento("pdf")}
                className="inline-flex h-8 items-center justify-center gap-1.5 rounded-lg bg-primary px-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/80"
              >
                Descargar el PDF escaneado
              </a>
            )}
            {texto !== null ? (
              <Card>
                <CardContent
                  className="py-6 text-sm leading-relaxed [&_h1]:font-titulos [&_h1]:text-xl [&_h1]:font-bold [&_h1]:mb-4
                    [&_h2]:font-titulos [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mt-6 [&_h2]:mb-2
                    [&_h3]:font-titulos [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-4 [&_h3]:mb-2
                    [&_p]:mb-3 [&_blockquote]:border-l-2 [&_blockquote]:border-borde-suave [&_blockquote]:pl-3
                    [&_blockquote]:text-tinta-suave [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-3 [&_ol]:list-decimal
                    [&_ol]:pl-5 [&_ol]:mb-3"
                >
                  <ReactMarkdown>{texto}</ReactMarkdown>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="py-8 text-center text-tinta-suave">
                  La transcripción todavía no está cargada; por ahora está el PDF escaneado.
                </CardContent>
              </Card>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
