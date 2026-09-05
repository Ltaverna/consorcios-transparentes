"use client";

import { createContext, useContext } from "react";
import type { Rol } from "@/lib/api";

/** Rol de la sesión del panel. Default "auditor": el provider se monta siempre en el layout
 *  del panel; el default solo aplica en tests que renderizan componentes sueltos. */
const RolContext = createContext<Rol>("auditor");

export function RolProvider({ rol, children }: { rol: Rol; children: React.ReactNode }) {
  return <RolContext.Provider value={rol}>{children}</RolContext.Provider>;
}

export function useRol(): Rol {
  return useContext(RolContext);
}
