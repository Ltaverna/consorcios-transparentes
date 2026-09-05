"use client";

import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api, ApiError, type Rol } from "@/lib/api";

function MensajeError({ mensaje }: { mensaje: string | null }) {
  if (!mensaje) return null;
  return (
    <p role="alert" className="text-[#B42318] text-sm">
      {mensaje}
    </p>
  );
}

function FormEquipo({ alEntrar }: { alEntrar: (rol: Rol) => void }) {
  const [email, setEmail] = useState("");
  const [clave, setClave] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function alEnviar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const res = await api.login(email, clave);
      alEntrar(res.rol);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={alEnviar} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email-equipo">Email</Label>
        <Input
          id="email-equipo"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="clave-equipo">Clave</Label>
        <Input
          id="clave-equipo"
          type="password"
          value={clave}
          onChange={(e) => setClave(e.target.value)}
          required
        />
      </div>
      <MensajeError mensaje={error} />
      <Button type="submit" disabled={enviando} className="w-full">
        {enviando ? "Entrando…" : "Entrar"}
      </Button>
    </form>
  );
}

function FormPropietario({ alEntrar }: { alEntrar: (rol: Rol) => void }) {
  const [uf, setUf] = useState("");
  const [codigo, setCodigo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function alEnviar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const res = await api.loginUnidad(Number(uf), codigo);
      alEntrar(res.rol);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo conectar con el servidor");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={alEnviar} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="uf-propietario">Unidad funcional (UF)</Label>
        <Input
          id="uf-propietario"
          type="number"
          value={uf}
          onChange={(e) => setUf(e.target.value)}
          required
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="codigo-propietario">Código de acceso</Label>
        <Input
          id="codigo-propietario"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          required
        />
      </div>
      <MensajeError mensaje={error} />
      <Button type="submit" disabled={enviando} className="w-full">
        {enviando ? "Entrando…" : "Entrar a mi unidad"}
      </Button>
    </form>
  );
}

export function FormulariosEntrar({ alEntrar }: { alEntrar: (rol: Rol) => void }) {
  return (
    <Tabs defaultValue="equipo">
      <TabsList className="w-full">
        <TabsTrigger value="equipo" className="flex-1">
          Equipo
        </TabsTrigger>
        <TabsTrigger value="propietario" className="flex-1">
          Propietario
        </TabsTrigger>
      </TabsList>
      <TabsContent value="equipo" className="pt-4">
        <FormEquipo alEntrar={alEntrar} />
      </TabsContent>
      <TabsContent value="propietario" className="pt-4">
        <FormPropietario alEntrar={alEntrar} />
      </TabsContent>
    </Tabs>
  );
}
