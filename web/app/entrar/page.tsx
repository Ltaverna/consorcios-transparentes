"use client";

import { useRouter } from "next/navigation";
import { FormulariosEntrar } from "@/components/login-forms";
import type { Rol } from "@/lib/api";

export default function EntrarPage() {
  const router = useRouter();

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
