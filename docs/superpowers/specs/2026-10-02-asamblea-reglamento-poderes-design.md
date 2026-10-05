# App de asamblea: reglamento, poderes con tope legal y proposiciones (CCyC 2060)

**Fecha:** 2026-10-02
**Estado:** en revisión del usuario
**Alcance:** parte **funcional** de la app de asamblea (`apps/asamblea/`), reutilizable para cualquier
asamblea. El **contenido** de la próxima asamblea (orden del día, preguntas, convocatoria, poder) queda
fuera de este ciclo: se carga como datos en `asamblea_content.py` cuando exista la convocatoria.

## Contexto

La app de asamblea es un **único `index.html`** generado por `make_votacion.py`, que embebe el contenido de
`asamblea_content.py` (dict `agenda/preguntas/convocatoria/poder`) y las unidades de `votacion_units.json`.
Se publica en Cloudflare Pages (`asamblea.neuralcore.dev`). El backend opcional `Code.gs` (Apps Script)
sincroniza el estado entre teléfonos y guarda historial. No tiene build ni tests hoy; la lógica de votación
vive como JavaScript inline dentro del HTML generado.

Auditoría de lo que **ya existe** (no hay que reconstruirlo):
- Doble mayoría del art. 2060 CCyC: computa unidades **y** porcentual a la vez; las abstenciones no suman.
- Reglas de mayoría seleccionables: absoluta (>50% del total), simple de presentes, dos tercios del total.
- Pestaña Proposiciones con registro de objeciones de ausentes.
- Poderes: el estado `S.poderes[uf]` ya admite guardar un string con el representante, pero sin validación.
- Unidades del mismo propietario ya se marcan en conjunto ("sibs").

## Restricciones transversales

- **Muy fácil de usar y responsive en teléfono y tablet.** El operador real es el moderador desde su
  teléfono, en vivo. Mantener la base responsive actual (tabs sticky, inputs a 16px, media queries). Ningún
  flujo nuevo puede empeorar eso.
- **Un solo archivo sin servidor**: el `index.html` generado debe seguir funcionando offline (sin depender
  de red en plena asamblea). Todo lo nuevo se embebe en build time.
- **Datos del consorcio**: el reglamento de copropiedad se versiona en `apps/asamblea/reglamento.md`
  (decisión del dueño; no es documento sensible y la app se publica igual). Es coherente con el patrón
  actual (`asamblea_content.py` ya versiona contenido del consorcio).

## Piezas

### A. Reglamento — pestaña nueva "Reglamento"

- `apps/asamblea/reglamento.md`: la transcripción del reglamento de copropiedad (ya obtenida del panel,
  468 líneas; encabezados `#`/`##`/`###` por artículo).
- `make_votacion.py` lee ese archivo y lo embebe en el `CONTENT` (nuevo campo `reglamento`).
- Nueva pestaña **"Reglamento"** en la barra de tabs (pasa de 5 a 6; las tabs ya hacen scroll horizontal
  en móvil).
- La vista renderiza el markdown con: **índice de artículos** navegable (anclas a cada `##`/`###`) y un
  **buscador** de texto que filtra/resalta. En móvil el índice va colapsado arriba.
- Desde la pieza B (poderes), un enlace "ver art. 25 h" salta al artículo en esta pestaña.

### B. Poderes con mandatario y validaciones (art. 25 h del reglamento)

Texto legal a respetar (art. Vigésimo Quinto, inc. h):
> "Un mismo mandatario no podrá representar a más de cinco propietarios, excluida su unidad. El
> administrador no podrá actuar como mandatario de ningún copropietario. En caso de existir establecido un
> condominio sobre alguna de las unidades, los titulares de él deberán unificar representación."

- **Modelo**: `S.poderes[uf]` pasa a identificar al **mandatario** de esa unidad. El mandatario es (a) un
  propietario presente, identificado por su UF, o (b) un tercero, identificado por nombre (+ DNI opcional).
  Se normaliza a una clave estable por mandatario para poder contar.
- **Conteo por propietario representado**: las unidades se agrupan por propietario (ya existe la noción de
  "sibs"); un mandatario que representa a una persona con varias unidades cuenta **1**. El tope es **5
  propietarios representados, excluida la unidad propia del mandatario**.
- **Validaciones**:
  - Al asignar el poder nº 6 a un mismo mandatario, la app **bloquea** la acción y explica por qué,
    citando el art. 25 h (con enlace a la pestaña Reglamento).
  - El **administrador** (marcado como tal en los datos) no puede seleccionarse como mandatario.
  - **Condominio**: los cotitulares de una unidad unifican representación (se asignan en bloque, como ya
    ocurre con las "sibs").
- **UI (móvil primero)**: al marcar una unidad como "viene con poder", un paso simple elige el mandatario
  (lista de presentes + opción "tercero con carta poder"). Cada mandatario muestra un contador
  **"representa N/5"**; al llegar a 5 queda visualmente lleno y el 6º no se habilita. El resumen de quórum
  y el acta (export) reflejan quién representa a quién.
- **Sincronización**: `Code.gs` y el protocolo `sync.send({t:'poder', …})` transportan el mandatario, no
  solo un booleano. Compatibilidad: estados viejos con `poder:true` se leen como "poder sin mandatario
  asignado" (se pide completarlo).

### C. Proposiciones según CCyC art. 2060

Regla vigente: si una decisión no reúne la mayoría absoluta sobre el total pero sí la de los presentes, es
una **proposición**; se comunica a los ausentes y queda **firme a los 15 días de notificados, salvo
oposición de igual mayoría** dentro de ese plazo.

- La app ya detecta "no hubo mayoría del total → proposición" y registra objeciones. Falta **computar la
  oposición**: sumar las objeciones de ausentes en **unidades y porcentual** y compararlas contra la misma
  mayoría que se exigía (doble mayoría), para decidir si la proposición **decae** o queda **firme** al
  vencer el plazo.
- Mostrar por proposición: la fecha de cierre (15 días desde la notificación), el avance de la oposición
  ("objeciones: X unidades / Y% — se necesita igual mayoría para tumbarla"), y el estado resultante
  (En circulación / Firme / Decaída).
- La fecha base de notificación es un dato editable por el moderador (cuándo se circuló).

### D. Mejoras de usabilidad

De la auditoría, acotadas y al servicio de la asamblea:
- Estado de **quórum** y de **proposición** siempre legibles de un vistazo en móvil (jerarquía visual,
  números grandes, sin scroll para lo esencial).
- Flujo del moderador: mínimos toques para marcar presente / con poder / voto; confirmaciones solo donde
  hay riesgo (p. ej. bloqueo del 6º poder).
- Accesibilidad: foco visible, roles ARIA en tabs y diálogos (ya hay base), contraste en estados de color
  (el poder en ámbar, el "lleno" del tope).
- La auditoría completa de usabilidad se detalla en el plan; acá se fija el criterio, no cada micro-ajuste.

### E. Fuera de alcance (este ciclo)

- Contenido de la asamblea nueva (orden del día, preguntas, convocatoria, poder) → datos en
  `asamblea_content.py` cuando exista la convocatoria.
- Ingesta de otros sistemas de liquidación (Consorcio Abierto, etc.).

## Testing

La lógica legal es crítica, así que se **extrae a funciones puras** y se cubre con tests; el resto (HTML,
estilos) se verifica a ojo en teléfono/tablet.

- **Extracción**: mover a un módulo JS testeable (o a funciones puras dentro del generado, exportables en
  test) el **cómputo de mayorías/quórum**, la **validación del tope de poderes** (conteo por propietario,
  exclusión de la unidad propia, admin excluido) y el **cómputo de la oposición del 2060**.
- **Casos de poderes**: mandatario con 5 propietarios (ok) y con 6 (bloqueado); mandatario con una persona
  de varias unidades (cuenta 1); administrador rechazado como mandatario; condominio unificado.
- **Casos de 2060**: proposición con oposición que alcanza igual mayoría (decae) y que no la alcanza
  (firme); doble mayoría (unidades y porcentual) en ambos ejes.
- **Generador**: `make_votacion.py` embebe `reglamento.md` y produce un `index.html` válido con la pestaña
  nueva (test de humo: el archivo generado contiene el índice del reglamento y el nuevo campo `reglamento`).
- Herramienta de test JS: la más liviana que no agregue build pesado (p. ej. node con un runner mínimo);
  se decide en el plan.

## Archivos

- Crear: `apps/asamblea/reglamento.md` (transcripción del reglamento de copropiedad).
- Modificar: `apps/asamblea/make_votacion.py` (embeber reglamento; pestaña y vista Reglamento; modelo de
  poderes con mandatario; validaciones; cómputo de proposiciones 2060; mejoras de UX).
- Modificar: `apps/asamblea/Code.gs` (persistir el mandatario del poder y el estado de proposiciones).
- Crear: tests de la lógica pura (poderes, mayorías, 2060) + test de humo del generador.
- Sin cambios en el motor ni en la API.

## Verificación

- Las tres suites de lógica en verde.
- `make_votacion.py` genera el `index.html` sin error y con la pestaña Reglamento.
- Prueba manual en teléfono y tablet: navegar el reglamento, asignar poderes hasta el bloqueo del 6º,
  simular una proposición con y sin oposición suficiente.
- Deploy a `asamblea.neuralcore.dev` (Cloudflare Pages), con confirmación del dueño.
