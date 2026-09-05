import { redirect } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { pedirServidor } from "@/lib/api-server";
import type { Yo, HallazgoResumen } from "@/lib/api";

export default async function PanelLayout({ children }: { children: React.ReactNode }) {
  const yo = await pedirServidor<Yo>("/auth/yo");
  if (yo.rol === "propietario") redirect("/mi-unidad");
  let pendientes = 0;
  try {
    pendientes = (await pedirServidor<HallazgoResumen[]>("/hallazgos?estado=pendiente")).length;
  } catch (e) {
    if ((e as { digest?: string })?.digest?.startsWith?.("NEXT_REDIRECT")) throw e;
    // el contador no puede tirar el panel
  }
  return (
    <div className="flex min-h-screen">
      <Sidebar rol={yo.rol} nombre={yo.nombre || yo.rol} pendientes={pendientes} activa="" />
      <main className="flex-1 min-w-0 p-6 pt-14 md:pt-6">{children}</main>
    </div>
  );
}
