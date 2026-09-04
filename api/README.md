# API del panel (Consorcio Transparente)

FastAPI + Postgres. Importa el motor (`engine/`) como biblioteca; requiere `pdftotext` (poppler).

## Desarrollo
    python3 -m venv .venv && .venv/bin/pip install -e ../engine -e '.[dev]'
    .venv/bin/python -m pytest -q                # tests (SQLite en memoria, storage en tmp)
    cp .env.example .env                          # completar
    .venv/bin/python cli.py init "Rivadavia 2069" --direccion "Av. Rivadavia 2069, CABA"
    .venv/bin/python cli.py usuario lucas@example.com "Lucas" auditor
    .venv/bin/uvicorn app.main:app --reload --port 8080

## Flujo
1. `POST /liquidaciones` (PDF + período) → procesa en background: cuadre → reglas → gastos → hallazgos.
2. `POST /liquidaciones/{id}/comprobantes` (ZIP de `ct descargar`) → cruce → documentos + hallazgos.
3. Revisar `GET /hallazgos`, cambiar estados, marcar `publicado`.
4. `POST /liquidaciones/{id}/publicar` → informes HTML/Excel en storage; el propietario entra
   con su código (`POST /auth/login-unidad`) y ve `/mi-unidad` e `/informes/{periodo}/{tipo}`.

Regla de oro: si la liquidación no cuadra (`no_cuadra`), no hay publicación posible — y reprocesar
retira los informes emitidos hasta que el auditor vuelva a publicar.

Nota para el front: `PUT /consorcio` reemplaza el dict de `umbrales` completo (semántica PUT); mandar
siempre todos los valores (el `GET` devuelve `umbrales` + `umbrales_default` para el round-trip). `{}` = reset.

## Producción (Plan 3)
Contenedor Docker (poppler incluido) o la máquina del auditor detrás de `cloudflared tunnel`
como `api-consorcio.neuralcore.dev`. Postgres Neon + Cloudflare R2 por variables `CT_*` (ver `.env.example`).
