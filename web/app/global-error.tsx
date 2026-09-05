"use client";

/** Frontera de error raíz: cubre errores lanzados por los layouts (p. ej. API caída),
 *  que el error.tsx de segmento no alcanza. */
export default function ErrorGlobal({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="es-AR">
      <body style={{ fontFamily: "system-ui", background: "#F6F8FB", color: "#1A2B3C", display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
        <div style={{ background: "#fff", border: "1px solid #E3E8EF", borderRadius: 8, padding: 32, textAlign: "center", maxWidth: 420 }}>
          <h1 style={{ color: "#123A5C", fontSize: 20, marginBottom: 8 }}>No se pudo conectar con el servidor</h1>
          <p style={{ color: "#5B6B7C", fontSize: 14, marginBottom: 16 }}>Verificá que la API esté corriendo y reintentá.</p>
          <button onClick={reset} style={{ background: "#123A5C", color: "#fff", border: 0, borderRadius: 6, padding: "10px 20px", cursor: "pointer" }}>
            Reintentar
          </button>
        </div>
      </body>
    </html>
  );
}
