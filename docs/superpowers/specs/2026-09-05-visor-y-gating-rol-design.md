# Visor seguro de comprobantes + panel de solo lectura por rol (diseño aprobado 05-09-2026)

Dos seguimientos del panel anotados en `docs/ESTADO.md`: el iframe de vista previa de comprobantes quedó
muerto cuando la descarga pasó a ser forzada (Plan 3, tarea A2), y los controles de auditor se muestran a
cualquier rol del equipo aunque la API les devuelva 403.

## 1. API — vista inline solo para el equipo

`GET /documentos/{d_id}/contenido` gana el query param `vista: bool = False`:

- **`vista=false` (default)**: igual que hoy — attachment forzado en local y en R2 (`descarga=True`).
- **`vista=true`**: sirve inline. Local: `Content-Disposition: inline`, conservando `X-Content-Type-Options:
  nosniff` y el content-type `application/pdf`. R2: `url_firmada(key, descarga=False)`.
- Autorización: el `requiere("auditor", "consejo", "moderador")` existente ya excluye propietarios; no se
  agrega superficie pública. `/informes/...` no se toca.

## 2. Front — visor en la ficha del hallazgo

- `web/lib/api.ts`: `urlContenidoDocumento(id, { vista })` agrega el query param.
- `web/components/hallazgos/ficha.tsx`: el `<iframe>` usa la URL con `vista=1` (vuelve a renderizar); el
  link con ícono queda como descarga (URL sin `vista`). Grid de 2 columnas y prop `conVisor` sin cambios.

## 3. Front — gating por rol

- Nuevo `web/components/rol-context.tsx`: `RolProvider` (client) + hook `useRol()`. El provider se monta en
  `web/app/panel/layout.tsx` con el `yo.rol` que el layout ya obtiene en el server.
- Se ocultan si `rol !== "auditor"`:
  - Ficha del hallazgo: `SelectorEstado`, `TogglePublicar`, `RespuestaAdmin` (el historial y una respuesta
    ya registrada siguen visibles como texto).
  - Liquidaciones: subir PDF, subir ZIP y el botón publicar del detalle.
  - Consorcio: edición de umbrales y generar código (la lista de unidades sigue visible).
- Sin rutas ni navegación nuevas: consejo/moderador ven todas las pantallas de lectura. El sidebar ya
  muestra el rol.

## 4. Errores y bordes

- PDF que el navegador no renderice embebido: fallback nativo del iframe; el link de descarga está al lado.
- `vista=1` pedido por un propietario → 403 del `requiere` existente (sin código nuevo).

## 5. Pruebas

- API (+1): con storage espía, `?vista=1` → `url_firmada(..., descarga=False)` y sin `vista` →
  `descarga=True`; en local, header `inline` vs `attachment`.
- Web (+2): la ficha renderiza el iframe con `vista=1` y el link de descarga sin `vista`; con rol `consejo`
  no aparecen los controles de auditor (ficha y subidas), con `auditor` sí.

## Fuera de alcance

Acciones propias para consejo/moderador (p. ej. comentar hallazgos), SSO de Google, visor para propietarios.
