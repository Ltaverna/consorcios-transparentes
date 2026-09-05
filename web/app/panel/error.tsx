"use client";

import { useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

/** Boundary de error del panel: evita la página de error genérica de Next si la API cae. */
export default function ErrorPanel({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-[60vh] p-6">
      <Card className="max-w-md w-full">
        <CardContent className="flex flex-col items-center gap-3 text-center py-8">
          <h1 className="font-titulos text-lg font-bold">Algo salió mal</h1>
          <p className="text-sm text-tinta-suave">
            No se pudo mostrar esta pantalla. Probá de nuevo en un momento.
          </p>
          <Button variant="outline" onClick={reset}>
            Reintentar
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
