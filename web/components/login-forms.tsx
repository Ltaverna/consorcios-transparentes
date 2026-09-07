"use client";

import { useState, useEffect, useRef } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api, type Rol } from "@/lib/api";
import { mensajeError } from "@/lib/formato";

function MensajeError({ mensaje }: { mensaje: string | null }) {
  if (!mensaje) return null;
  return (
    <p role="alert" className="text-[#B42318] text-sm">
      {mensaje}
    </p>
  );
}

interface GoogleGSI {
  accounts: {
    id: {
      initialize(cfg: { client_id: string; callback: (resp: { credential: string }) => void }): void;
      renderButton(el: HTMLElement, cfg: { theme: string; size: string }): void;
    };
  };
}

function sdkGoogle(): GoogleGSI | undefined {
  return (window as unknown as { google?: GoogleGSI }).google;
}

function BotonGoogle({ alEntrar, alError }: { alEntrar: (rol: Rol) => void; alError: (m: string) => void }) {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const contenedor = useRef<HTMLDivElement>(null);
  const alEntrarRef = useRef(alEntrar);
  const alErrorRef = useRef(alError);
  alEntrarRef.current = alEntrar;
  alErrorRef.current = alError;

  useEffect(() => {
    if (!clientId) return;
    const iniciar = () => {
      const google = sdkGoogle();
      if (!google?.accounts?.id || !contenedor.current) return;
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (resp: { credential: string }) => {
          try {
            const res = await api.loginGoogle(resp.credential);
            alEntrarRef.current(res.rol);
          } catch (err) {
            alErrorRef.current(mensajeError(err));
          }
        },
      });
      google.accounts.id.renderButton(contenedor.current, { theme: "outline", size: "large" });
    };
    if (sdkGoogle()?.accounts?.id) {
      iniciar();
      return;
    }
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = iniciar;
    document.head.appendChild(s);
  }, [clientId]);

  if (!clientId) return null;
  return (
    <div className="flex flex-col gap-3 pt-3">
      <div className="flex items-center gap-2 text-xs text-tinta-suave">
        <div className="h-px flex-1 bg-borde-suave" />
        o
        <div className="h-px flex-1 bg-borde-suave" />
      </div>
      <div ref={contenedor} data-testid="boton-google" className="flex justify-center" />
    </div>
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
      setError(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
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
      <BotonGoogle alEntrar={alEntrar} alError={setError} />
    </>
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
      setError(mensajeError(err));
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
        <p className="text-sm text-tinta-suave">
          Es el código que te entregó el consejo o el auditor. Si no lo tenés, pedilo en la administración del consorcio.
        </p>
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
    <Tabs defaultValue="propietario">
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
