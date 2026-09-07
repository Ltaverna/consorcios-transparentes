"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { FormulariosEntrar } from "@/components/login-forms";
import { api, type Rol } from "@/lib/api";

export default function EntrarPage() {
  const router = useRouter();

  // Si ya hay sesión activa, redirigir silenciosamente. El formulario se muestra
  // de inmediato (sin bloqueo) y la redirección ocurre sólo si el check tiene éxito.
  useEffect(() => {
    api.yo().then((yo) => {
      router.replace(yo.rol === "propietario" ? "/mi-unidad" : "/panel");
    }).catch(() => {
      // Sin sesión o error de red: quedarse en esta página, sin mensaje de error.
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function alEntrar(rol: Rol) {
    router.push(rol === "propietario" ? "/mi-unidad" : "/panel");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-fondo px-4">
      <div className="w-full max-w-sm flex flex-col gap-6">
        <div className="text-center">
          <h1 className="font-titulos text-2xl font-bold text-institucional">Consorcio Transparente</h1>
          <p className="text-tinta-suave text-sm">Panel de auditoría · Rivadavia 2069</p>
        </div>
        <FormulariosEntrar alEntrar={alEntrar} />
      </div>
    </div>
  );
}
