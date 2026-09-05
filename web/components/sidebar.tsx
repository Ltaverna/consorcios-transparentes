"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { SearchCheck, FileSpreadsheet, Building2, Menu } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

interface SidebarProps {
  rol: string;
  nombre: string;
  pendientes: number;
  activa: string;
}

const SECCIONES = [
  { href: "/panel/hallazgos", texto: "Hallazgos", Icono: SearchCheck },
  { href: "/panel/liquidaciones", texto: "Liquidaciones", Icono: FileSpreadsheet },
  { href: "/panel/consorcio", texto: "Consorcio", Icono: Building2 },
];

function Marca() {
  return (
    <div className="px-4 py-4 border-b border-white/15">
      <p className="font-titulos font-bold">Consorcio Transparente</p>
    </div>
  );
}

function Nav({ activa, pendientes }: { activa: string; pendientes: number }) {
  return (
    <nav className="flex flex-col py-2">
      {SECCIONES.map(({ href, texto, Icono }) => {
        const activo = activa.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 border-l-2 border-transparent",
              activo
                ? "bg-white/10 border-[#4ADE80]"
                : "opacity-75 hover:opacity-100 hover:bg-white/5 transition-colors"
            )}
          >
            <Icono className="w-4 h-4" />
            <span>{texto}</span>
            {texto === "Hallazgos" && pendientes > 0 && (
              <span className="bg-[#B42318] rounded-full px-2 text-xs">{pendientes}</span>
            )}
          </Link>
        );
      })}
      <span className="flex items-center gap-2 px-4 py-2.5 opacity-40 cursor-default">
        Asamblea (pronto)
      </span>
    </nav>
  );
}

function Pie({ nombre, rol }: { nombre: string; rol: string }) {
  async function salir() {
    try {
      await api.salir();
    } catch {
      // igual redirigimos: no queremos dejar al usuario varado en el panel
    } finally {
      window.location.href = "/entrar";
    }
  }

  return (
    <div className="mt-auto px-4 py-4 border-t border-white/15 flex flex-col gap-2">
      <p className="text-xs opacity-75">
        {nombre} · {rol}
      </p>
      <button
        onClick={salir}
        className="text-left text-sm opacity-90 hover:opacity-100 underline-offset-2 hover:underline"
      >
        Salir
      </button>
    </div>
  );
}

export function Sidebar({ rol, nombre, pendientes, activa }: SidebarProps) {
  const pathname = usePathname();
  const activaEfectiva = activa || pathname || "";
  const [abierta, setAbierta] = useState(false);

  return (
    <>
      <aside className="hidden md:flex w-52 shrink-0 min-h-screen flex-col bg-[#123A5C] text-white">
        <Marca />
        <Nav activa={activaEfectiva} pendientes={pendientes} />
        <Pie nombre={nombre} rol={rol} />
      </aside>

      <button
        aria-label="Abrir menú"
        onClick={() => setAbierta(true)}
        className="md:hidden fixed top-3 left-3 z-40 p-2 rounded-md bg-[#123A5C] text-white"
      >
        <Menu className="w-5 h-5" />
      </button>

      <Sheet open={abierta} onOpenChange={setAbierta}>
        <SheetContent
          side="left"
          className="bg-[#123A5C] text-white border-none p-0 flex flex-col"
        >
          <SheetTitle className="sr-only">Menú del panel</SheetTitle>
          <Marca />
          <Nav activa={activaEfectiva} pendientes={pendientes} />
          <Pie nombre={nombre} rol={rol} />
        </SheetContent>
      </Sheet>
    </>
  );
}
