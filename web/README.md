# Panel web (Consorcio Transparente)

Next.js + Tailwind + shadcn/ui sobre la API (`api/`). Theme institucional claro (spec en
`docs/superpowers/specs/2026-09-04-panel-web-design.md`).

## Desarrollo
    npm install
    cp .env.local.example .env.local        # apunta a la API (dev: http://localhost:8080)
    npm run dev                              # necesita la API corriendo (ver api/README.md)
    npm test                                 # Vitest + Testing Library (API mockeada con MSW)

## Rutas
`/entrar` (equipo o propietario) · `/panel/hallazgos` (triage con drawer; ficha linkeable en
`/panel/hallazgos/[id]`) · `/panel/liquidaciones` (subir PDF y ZIP de comprobantes; detalle en
`/panel/liquidaciones/[id]` con cuadre, gastos y publicar informe) · `/panel/consorcio` (umbrales,
unidades, códigos) · `/mi-unidad` (propietario: informe embebido + estado de cuenta).

## Notas
- `proxy.ts` — guardia de sesión con la convención de Next 16 (migrada desde `middleware.ts` en el deploy).
- Deploy (Plan 3, adapter ya configurado: `wrangler.jsonc` + `npm run deploy:cf`): Cloudflare Workers vía OpenNext
  como `panel-consorcio.neuralcore.dev`, mismo sitio que la API
  (`api-consorcio.neuralcore.dev`) para que viaje la cookie de sesión.
