# App de asamblea: reglamento, poderes y proposiciones 2060 — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar a la app de asamblea una pestaña de Reglamento de copropiedad, poderes con mandatario validados contra el art. 25 h (tope 5 propietarios, admin excluido, condominio unificado) y el cómputo de proposiciones según el art. 2060 CCyC, con la lógica legal extraída a un módulo testeado.

**Architecture:** La app es un único `index.html` generado por `make_votacion.py` (reemplaza marcadores `__DATA__`/`__CONTENT__` en un string HTML y escribe `pages-out/index.html`). Se agrega un marcador `__LOGICA__` que embebe `apps/asamblea/logica.js` — un módulo de **funciones puras** (mayorías, tope de poderes, proposiciones 2060) que además se importa desde tests con `node:test`. El reglamento vive en `apps/asamblea/reglamento.md`, versionado, y se embebe como un campo más del contenido.

**Tech Stack:** Python (generador), HTML/CSS/JS vanilla (app, sin build ni framework), Node 22.11 `node:test` (tests de la lógica pura), Google Apps Script (`Code.gs`, sincronización).

**Spec:** `docs/superpowers/specs/2026-10-02-asamblea-reglamento-poderes-design.md`

**Comandos de test:**
- Lógica: `cd apps/asamblea && node --test`
- Generador: `cd apps/asamblea && python3 make_votacion.py` (debe imprimir `ok` y generar el HTML)

**Orden de ejecución sugerido:** Tareas 1→3 son lo imprescindible para la asamblea (base + reglamento + poderes). Tareas 4→7 (proposiciones 2060, persistencia, identidad visual, panel de cumplimiento) son la segunda fase. La Task 7 reúne la lógica de las 1/3/4, así que va después de ellas. Cada tarea deja la app funcionando.

---

## File Structure

- `apps/asamblea/logica.js` — **nuevo**. Funciones puras exportadas: `veredicto`, `contarRepresentados`, `puedeAsignarMandatario`, `evaluarProposicion`. Sin estado global, sin DOM. Se embebe en el HTML y se importa en tests.
- `apps/asamblea/logica.test.mjs` — **nuevo**. Tests `node:test` de `logica.js`.
- `apps/asamblea/reglamento.md` — **nuevo**. Transcripción del reglamento de copropiedad (ya disponible en `/tmp/reglamento.md`, obtenida del panel).
- `apps/asamblea/make_votacion.py` — **modificar**. Embeber `logica.js` (marcador `__LOGICA__`) y `reglamento.md` (campo `reglamento` en `CONTENT`); usar `veredicto` del módulo; agregar pestaña/vista Reglamento; UI de poderes con mandatario; UI de estados de proposición; marcar al administrador.
- `apps/asamblea/votacion_units.json` — **modificar**. Agregar `"admin": true` a la unidad del administrador si es propietario (en Rivadavia el admin no es propietario; ver Task 3).
- `apps/asamblea/Code.gs` — **modificar**. Persistir el mandatario de cada poder y el estado de proposiciones.

---

## Task 1: Módulo de lógica pura + tests, con `veredicto` extraída

Extrae la función de mayorías a un módulo puro testeable y monta el runner, sin cambiar el comportamiento de la app.

**Files:**
- Create: `apps/asamblea/logica.js`
- Create: `apps/asamblea/logica.test.mjs`
- Modify: `apps/asamblea/make_votacion.py` (embeber el módulo; reemplazar el `verdict` inline por el del módulo)

Contexto: hoy `make_votacion.py` tiene inline (≈ línea 433) esta función, que decide si una opción gana según la regla y la doble mayoría (unidades `o.n` y porcentual `o.pct`):

```javascript
function verdict(m, c, o){
  if(o.abst) return null;
  let needN, needPct, base;
  if(m.regla==='abs'){ needN = N/2; needPct = TOTAL_PCT/2; base='del total'; }
  else if(m.regla==='2/3'){ needN = N*2/3; needPct = TOTAL_PCT*2/3; base='del total'; }
  else { needN = c.partN/2; needPct = c.partPct/2; base='de los presentes'; }
  const okN = m.regla==='2/3' ? o.n >= needN : o.n > needN;
  const okP = m.regla==='2/3' ? o.pct >= needPct : o.pct > needPct;
  return {ok: okN && okP, okN, okP, needN, needPct, base};
}
```

- [ ] **Step 1: Escribir el módulo con `veredicto` (función pura equivalente)**

Crear `apps/asamblea/logica.js`. Debe funcionar tanto embebido en el navegador (sin `export`) como importado en Node. Patrón: definir en un objeto global y exportar condicionalmente.

```javascript
// Lógica pura de la asamblea. Sin DOM ni estado global: entra data, sale resultado.
// Se embebe en index.html (make_votacion.py) y se importa desde logica.test.mjs.
const CTLogica = (function () {
  // Veredicto de una opción de moción según la regla y la doble mayoría (unidades y porcentual).
  // regla: 'abs' (>50% del total), '2/3' (>=2/3 del total), 'pres' (>50% de los presentes).
  // o: {n, pct, abst}; totales: {N, totalPct}; part: {partN, partPct} (presentes+poderes).
  function veredicto(regla, o, totales, part) {
    if (o.abst) return null;
    let needN, needPct, base;
    if (regla === 'abs') { needN = totales.N / 2; needPct = totales.totalPct / 2; base = 'del total'; }
    else if (regla === '2/3') { needN = totales.N * 2 / 3; needPct = totales.totalPct * 2 / 3; base = 'del total'; }
    else { needN = part.partN / 2; needPct = part.partPct / 2; base = 'de los presentes'; }
    const okN = regla === '2/3' ? o.n >= needN : o.n > needN;
    const okP = regla === '2/3' ? o.pct >= needPct : o.pct > needPct;
    return { ok: okN && okP, okN, okP, needN, needPct, base };
  }

  return { veredicto };
})();
if (typeof module !== 'undefined' && module.exports) module.exports = CTLogica;
```

- [ ] **Step 2: Escribir los tests de `veredicto` (fallan: no existe el módulo aún… ya lo creaste en Step 1, así que acá verificás que pasan)**

Crear `apps/asamblea/logica.test.mjs`:

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { veredicto } = require('./logica.js');

const TOT = { N: 100, totalPct: 100 };
const PART = { partN: 60, partPct: 60 };

test('abs: gana si supera el 50% del total en unidades y porcentual', () => {
  const v = veredicto('abs', { n: 51, pct: 51, abst: false }, TOT, PART);
  assert.equal(v.ok, true);
});

test('abs: no alcanza si una de las dos mayorías falla', () => {
  const v = veredicto('abs', { n: 51, pct: 49, abst: false }, TOT, PART);
  assert.equal(v.ok, false);
});

test('2/3: usa >= y se mide sobre el total', () => {
  const v = veredicto('2/3', { n: 67, pct: 67, abst: false }, TOT, PART);
  assert.equal(v.ok, true);
});

test('pres: se mide sobre los presentes', () => {
  const v = veredicto('pres', { n: 31, pct: 31, abst: false }, TOT, PART);
  assert.equal(v.ok, true);  // 31 > 60/2
});

test('abstención devuelve null', () => {
  assert.equal(veredicto('abs', { n: 0, pct: 0, abst: true }, TOT, PART), null);
});
```

- [ ] **Step 3: Correr los tests**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && node --test`
Expected: PASS (5 tests).

- [ ] **Step 4: Embeber el módulo en el HTML generado y usarlo**

En `make_votacion.py`:
1. Cerca del header Python (después de `SC = HERE + "/"`), leer el módulo:
   ```python
   LOGICA = open(SC + "logica.js", encoding="utf-8").read()
   ```
2. En el string `HTML`, agregar un `<script>__LOGICA__</script>` **antes** del `<script>` principal de la app (para que `CTLogica` exista cuando corra la app).
3. En el `.replace(...)` final, agregar `.replace("__LOGICA__", LOGICA)`.
4. Reemplazar la definición inline de `function verdict(m,c,o){...}` por un wrapper que delega en el módulo (mantiene la firma que usa el resto del código):
   ```javascript
   function verdict(m, c, o){ return CTLogica.veredicto(m.regla, o, {N:N, totalPct:TOTAL_PCT}, {partN:c.partN, partPct:c.partPct}); }
   ```

- [ ] **Step 5: Regenerar y verificar que la app sigue igual**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && python3 make_votacion.py`
Expected: imprime `ok`. Abrir `pages-out/index.html` en el navegador: la pestaña Votar computa las mayorías igual que antes (el `<script>` del módulo aparece embebido; `CTLogica` está definido).

- [ ] **Step 6: Commit**

```bash
cd /opt/consorcios-transparentes
git add apps/asamblea/logica.js apps/asamblea/logica.test.mjs apps/asamblea/make_votacion.py
git commit -m "Asamblea: lógica de mayorías a módulo puro testeado (node:test)"
```

---

## Task 2: Pestaña Reglamento (índice + buscador)

**Files:**
- Create: `apps/asamblea/reglamento.md`
- Modify: `apps/asamblea/make_votacion.py`

- [ ] **Step 1: Traer el reglamento al repo**

```bash
cp /tmp/reglamento.md /opt/consorcios-transparentes/apps/asamblea/reglamento.md
```
Verificar: `head -1 apps/asamblea/reglamento.md` → `# Reglamento de Copropiedad y Administración — Edificio Avenida Rivadavia 2067/2069/2071`.

Si `/tmp/reglamento.md` ya no existe, re-obtenerlo del panel (endpoint `GET /consorcio/reglamento/transcripcion`, ver el script del historial de esta sesión) o pedírselo al dueño.

- [ ] **Step 2: Embeber el reglamento en el contenido**

En `make_votacion.py`:
```python
REGLAMENTO = open(SC + "reglamento.md", encoding="utf-8").read()
CONTENT = json.dumps(dict(agenda=AGENDA, preguntas=PREGUNTAS, convocatoria=CONVOCATORIA,
                          poder=PODER, reglamento=REGLAMENTO), ensure_ascii=False).replace("</", "<\\/")
```

- [ ] **Step 3: Agregar la pestaña y la vista**

En el HTML (`make_votacion.py`), en `<nav class="tabs">` (≈ línea 271) agregar el botón al final:
```html
<button role="tab" data-tab="reglamento" aria-selected="false">Reglamento</button>
```
Agregar la vista (junto a las otras `view`, ≈ línea 316):
```html
<div class="wrap view" id="view-reglamento">
  <h2 class="sec">Reglamento de copropiedad</h2>
  <input id="regBuscar" type="search" placeholder="Buscar en el reglamento…" aria-label="Buscar en el reglamento" style="width:100%;padding:10px;font-size:16px;margin-bottom:10px">
  <details id="regIndice" class="card"><summary>Índice de artículos</summary><nav id="regIndiceNav"></nav></details>
  <div id="regTexto" class="doc"></div>
</div>
```

- [ ] **Step 4: Render del reglamento (markdown liviano + índice + búsqueda)**

En el JS principal, agregar una función que convierta el markdown a HTML con el mínimo necesario (encabezados `#`/`##`/`###` → `h2/h3/h4` con `id` de ancla; párrafos; negritas `**`), arme el índice con anclas, y filtre/resalte al buscar. Engancharla en el hook de render por pestaña (el bloque `renderAll = function(){ ... }` del final, ≈ cierre del archivo), agregando `else if(TAB==='reglamento') renderReglamento();`.

```javascript
function _mdInline(s){ return esc(s).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>'); }
function renderReglamento(){
  const md = C.reglamento || '';
  const nav = []; let html = ''; let i = 0;
  for(const raw of md.split('\n')){
    const line = raw.replace(/\r$/,'');
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if(h){ const lvl=h[1].length, id='reg-'+(i++); const txt=h[2];
      if(lvl>=3) nav.push(`<a href="#${id}">${esc(txt)}</a>`);
      html += `<h${lvl+1} id="${id}">${_mdInline(txt)}</h${lvl+1}>`;
    } else if(line.trim()==='') { html += ''; }
    else { html += `<p>${_mdInline(line)}</p>`; }
  }
  $('#regTexto').innerHTML = html;
  $('#regIndiceNav').innerHTML = nav.join('');
}
function filtrarReglamento(q){
  q = (q||'').trim().toLowerCase();
  for(const el of $('#regTexto').querySelectorAll('p,h2,h3,h4,h5')){
    const hit = !q || el.textContent.toLowerCase().includes(q);
    el.style.display = hit ? '' : 'none';
  }
}
```
Y el listener (en el bloque de binds de inputs): `$('#regBuscar').addEventListener('input', e=>filtrarReglamento(e.target.value));`

- [ ] **Step 5: Enlace al art. 25 h desde Documentos/poderes (opcional, barato)**

En la descripción de ayuda del punto de poderes y en el bloqueo del 6º poder (Task 3), incluir un enlace `onclick` que haga `setTab('reglamento')` y foco en el artículo 25 (anclarlo por texto al render). Dejar el gancho: una función `irAReglamento(texto)` que cambia de pestaña y hace scroll al primer encabezado cuyo texto incluya `texto`.

```javascript
function irAReglamento(texto){ setTab('reglamento'); setTimeout(()=>{ const t=texto.toLowerCase();
  for(const el of $('#regTexto').querySelectorAll('h2,h3,h4')){ if(el.textContent.toLowerCase().includes(t)){ el.scrollIntoView({behavior:'smooth',block:'start'}); break; } } }, 60); }
```

- [ ] **Step 6: Regenerar y verificar en móvil**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && python3 make_votacion.py`
Expected: `ok`. Abrir el HTML: la pestaña **Reglamento** muestra el texto, el índice navega a los artículos, el buscador filtra. Probar en viewport angosto (DevTools, 390px).

- [ ] **Step 7: Commit**

```bash
cd /opt/consorcios-transparentes
git add apps/asamblea/reglamento.md apps/asamblea/make_votacion.py
git commit -m "Asamblea: pestaña Reglamento con índice y buscador"
```

---

## Task 3: Poderes con mandatario y validaciones del art. 25 h

**Files:**
- Modify: `apps/asamblea/logica.js` (+ tests en `logica.test.mjs`)
- Modify: `apps/asamblea/votacion_units.json` (marcar admin si corresponde)
- Modify: `apps/asamblea/make_votacion.py` (modelo de poder, UI, validación)

Regla (art. 25 h): un mandatario representa a lo sumo **5 propietarios, excluida su unidad**; el **administrador** no puede ser mandatario; **condominio** (misma unidad con varios titulares) unifica representación. El conteo es **por propietario** (una persona con varias unidades = 1).

Modelo nuevo: `S.poderes[uf]` deja de ser `true`/string-libre y pasa a ser **la clave del mandatario** (string). La clave del mandatario es el nombre del propietario representante (campo `prop`) si es un propietario, o `tercero:<nombre>` si es un apoderado externo. Dos unidades representadas por el mismo mandatario comparten esa clave.

- [ ] **Step 1: Tests de la lógica de tope (fallan)**

Agregar a `apps/asamblea/logica.test.mjs`:

```javascript
const { contarRepresentados, puedeAsignarMandatario } = require('./logica.js');

// units: [{uf, prop, admin?}]; poderes: {uf: claveMandatario}
const UNITS3 = [
  {uf:1, prop:'A'}, {uf:2, prop:'A'},      // A tiene 2 unidades
  {uf:3, prop:'B'}, {uf:4, prop:'C'}, {uf:5, prop:'D'},
  {uf:6, prop:'E'}, {uf:7, prop:'F'}, {uf:8, prop:'ADMIN', admin:true},
];

test('cuenta propietarios representados, no unidades', () => {
  const poderes = {1:'MAND', 2:'MAND'};  // A (2 unidades) por MAND
  assert.equal(contarRepresentados('MAND', poderes, UNITS3), 1);
});

test('permite hasta 5 propietarios y bloquea el 6º', () => {
  const poderes = {3:'MAND',4:'MAND',5:'MAND',6:'MAND',7:'MAND'}; // B..F = 5 props
  // sexto: intentar que MAND represente a A (uf 1)
  const r = puedeAsignarMandatario('MAND', 1, poderes, UNITS3);
  assert.equal(r.ok, false);
  assert.match(r.motivo, /cinco|5/i);
});

test('el administrador no puede ser mandatario', () => {
  const r = puedeAsignarMandatario('ADMIN', 3, {}, UNITS3);
  assert.equal(r.ok, false);
  assert.match(r.motivo, /administrador/i);
});

test('reasignar una unidad ya contada al mismo mandatario no suma de más', () => {
  const poderes = {3:'MAND',4:'MAND',5:'MAND',6:'MAND',7:'MAND'};
  const r = puedeAsignarMandatario('MAND', 3, poderes, UNITS3); // ya la representa
  assert.equal(r.ok, true);
});
```

- [ ] **Step 2: Correr para verlos fallar**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && node --test`
Expected: FAIL (funciones no exportadas).

- [ ] **Step 3: Implementar la lógica en `logica.js`**

Agregar dentro del IIFE (antes del `return`) y exponerlas en el `return`:

```javascript
  // Clave del propietario de una unidad (agrupa condominio/múltiples unidades por 'prop').
  function _propDe(uf, units){ const u = units.find(x => x.uf === uf); return u ? u.prop : null; }

  // Cuántos propietarios DISTINTOS representa un mandatario (por 'prop').
  function contarRepresentados(mandatario, poderes, units){
    const props = new Set();
    for(const uf in poderes){ if(poderes[uf] === mandatario){ const p = _propDe(Number(uf), units); if(p) props.add(p); } }
    return props.size;
  }

  // ¿Puede 'mandatario' tomar el poder de la unidad 'uf'? Aplica art. 25 h.
  function puedeAsignarMandatario(mandatario, uf, poderes, units){
    const u = units.find(x => x.uf === uf);
    const mandUnit = units.find(x => x.prop === mandatario || ('tercero:' + x.prop) === mandatario);
    if(mandUnit && mandUnit.admin) return { ok:false, motivo:'El administrador no puede actuar como mandatario (art. 25 h).' };
    // propietarios ya representados por este mandatario, excluyendo al de la unidad que se intenta asignar
    const propDeUf = u ? u.prop : null;
    const props = new Set();
    for(const k in poderes){ if(poderes[k] === mandatario){ const p = _propDe(Number(k), units); if(p && p !== propDeUf) props.add(p); } }
    if(props.size >= 5) return { ok:false, motivo:'Un mandatario no puede representar a más de cinco propietarios (art. 25 h).' };
    return { ok:true };
  }
```
Y en el `return`: `return { veredicto, contarRepresentados, puedeAsignarMandatario };`

- [ ] **Step 4: Correr los tests — deben pasar**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && node --test`
Expected: PASS (todos, incluidos los de Task 1).

- [ ] **Step 5: Marcar al administrador en los datos**

En Rivadavia el administrador (Almazare) **no es propietario**, así que no está en `votacion_units.json` y la regla se cumple sola para la lista de propietarios. Dejar documentado en el `LEEME.txt` del deploy: *si el administrador fuera propietario, agregar `"admin": true` a su unidad en `votacion_units.json` para que la app lo excluya como mandatario.* No se requiere cambio de datos ahora.

- [ ] **Step 6: Cambiar el modelo y la UI de poderes en el generado**

En `make_votacion.py`:
1. `setPoder(u, val)` (≈ línea 521): cuando `val` es un mandatario (string), antes de asignarlo llamar a la validación; si falla, no asignar y mostrar el motivo con enlace al reglamento:
   ```javascript
   function setPoder(u, mandatario){
     if(mandatario){
       const r = CTLogica.puedeAsignarMandatario(mandatario, u.uf, S.poderes, UNITS);
       if(!r.ok){ toast(r.motivo); return; }
       S.poderes[u.uf]=mandatario; delete S.presentes[u.uf];
     } else { delete S.poderes[u.uf]; if(!S.presentes[u.uf]) for(const m of S.mociones) delete m.votos[u.uf]; }
     sync.send({t:'poder', uf:u.uf, v:mandatario||false});
   }
   ```
2. El input "Representado por" (≈ línea 479) pasa de texto libre a un **selector** de mandatario: los propietarios presentes (no admin) + opción "Tercero con carta poder" (que pide nombre). Al elegir, llama `setPoder(u, clave)`. Mostrar junto al poder el contador `representa N/5` usando `CTLogica.contarRepresentados(clave, S.poderes, UNITS)`; al llegar a 5, deshabilitar ese mandatario en los demás selectores.
3. Donde se togglea "Poder" sin mandatario aún (los chips de la vista lista, `rpoder`), permitir marcar "viene con poder" y pedir el mandatario en un paso siguiente (no bloquear el marcado inicial; la validación se aplica al asignar el mandatario).
4. En el bloqueo, el `toast` incluye un enlace "ver art. 25 h" → `irAReglamento('Representación')` (función de Task 2).

- [ ] **Step 7: Regenerar y probar el flujo**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && python3 make_votacion.py`
Expected: `ok`. En el navegador (viewport angosto): asignar un mandatario a 5 propietarios funciona; el 6º muestra el aviso y no se asigna; el contador `N/5` se ve; un propietario con varias unidades cuenta 1.

- [ ] **Step 8: Commit**

```bash
cd /opt/consorcios-transparentes
git add apps/asamblea/logica.js apps/asamblea/logica.test.mjs apps/asamblea/make_votacion.py apps/asamblea/deploy/LEEME.txt
git commit -m "Asamblea: poderes con mandatario y tope del art. 25 h (5 propietarios, admin excluido)"
```

---

## Task 4: Proposiciones según CCyC art. 2060 (cómputo de la oposición)

**Files:**
- Modify: `apps/asamblea/logica.js` (+ tests)
- Modify: `apps/asamblea/make_votacion.py` (vista Proposiciones)

Regla: si una decisión no reúne mayoría absoluta sobre el total pero sí de presentes, es **proposición**; se circula a ausentes y queda **firme a los 15 días salvo oposición de igual mayoría** (doble mayoría: unidades y porcentual) dentro del plazo.

- [ ] **Step 1: Tests (fallan)**

Agregar a `logica.test.mjs`:

```javascript
const { evaluarProposicion } = require('./logica.js');

// oposicion: {n, pct} de ausentes que objetan; totales {N, totalPct}; vencida: bool
test('firme si la oposición no alcanza la mayoría absoluta del total', () => {
  const r = evaluarProposicion({n:10, pct:10}, {N:100, totalPct:100}, true);
  assert.equal(r.estado, 'firme');
});
test('decae si la oposición alcanza igual mayoría (ambos ejes)', () => {
  const r = evaluarProposicion({n:51, pct:51}, {N:100, totalPct:100}, true);
  assert.equal(r.estado, 'decaida');
});
test('en una sola dimensión no alcanza: sigue firme', () => {
  const r = evaluarProposicion({n:51, pct:49}, {N:100, totalPct:100}, true);
  assert.equal(r.estado, 'firme');
});
test('antes del vencimiento está en circulación', () => {
  const r = evaluarProposicion({n:10, pct:10}, {N:100, totalPct:100}, false);
  assert.equal(r.estado, 'circulando');
});
```

- [ ] **Step 2: Correr para verlos fallar**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && node --test`
Expected: FAIL.

- [ ] **Step 3: Implementar en `logica.js`**

```javascript
  // Estado de una proposición del art. 2060. La oposición tumba la proposición solo si
  // alcanza la MISMA mayoría absoluta del total (doble: unidades y porcentual).
  function evaluarProposicion(oposicion, totales, vencida){
    const tumba = oposicion.n > totales.N/2 && oposicion.pct > totales.totalPct/2;
    if(tumba) return { estado:'decaida', tumba:true };
    if(!vencida) return { estado:'circulando', tumba:false };
    return { estado:'firme', tumba:false };
  }
```
Exponer en el `return`.

- [ ] **Step 4: Correr — pasan**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && node --test`
Expected: PASS (todos).

- [ ] **Step 5: Usar el cómputo en la vista Proposiciones**

En `renderPropos()` (generado), para cada moción que quedó como proposición: sumar las objeciones de ausentes en unidades y porcentual (ya hay `S.objeciones`), llamar `CTLogica.evaluarProposicion({n,pct}, {N,totalPct:TOTAL_PCT}, Date.now()>DEADLINE)` y mostrar el estado (**En circulación** / **Firme** / **Decaída**), la fecha de cierre (`DEADLINE`, ya existe) y el avance "oposición: X UF / Y% — se necesita mayoría absoluta del total para tumbarla". La fecha de notificación base editable por el moderador (campo que setea `DEADLINE = notificacion + 15 días`).

- [ ] **Step 6: Regenerar y verificar**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && python3 make_votacion.py`
Expected: `ok`. Simular una proposición con objeciones por debajo y por encima de la mayoría; el estado cambia de Firme a Decaída al cruzar ambos ejes.

- [ ] **Step 7: Commit**

```bash
cd /opt/consorcios-transparentes
git add apps/asamblea/logica.js apps/asamblea/logica.test.mjs apps/asamblea/make_votacion.py
git commit -m "Asamblea: cómputo de proposiciones y oposición según art. 2060 CCyC"
```

---

## Task 5: Sincronización y exportación a Google Sheets (`Code.gs`)

Hoy `Code.gs` (Apps Script) sincroniza el estado entre dispositivos y **exporta a una hoja de Google** un resumen (quórum y mociones, ver el bloque `out = [...]` de la hoja "Resultados"). Esta tarea hace dos cosas: (a) que la sincronización y la exportación **reflejen todo lo nuevo** (mandatario de cada poder, estado de proposiciones, panel de cumplimiento), y (b) **mejorar la exportación** donde se pueda.

**Files:**
- Modify: `apps/asamblea/Code.gs`

- [ ] **Step 1: Auditar la exportación actual**

Leer `Code.gs` completo y anotar: qué hojas/pestañas escribe, qué columnas, qué eventos sincroniza (`presente`, `poder`, `voto`, …), y cómo reconstruye el estado para un cliente nuevo. Pegar el inventario en el cuerpo del commit. Esto fija qué hay antes de tocar.

- [ ] **Step 2: Sincronizar los campos nuevos**

- `poder`: hoy `{t:'poder', uf, v:bool}`. Ahora `v` es la **clave del mandatario** (string) o `false`. Guardar el valor tal cual (no forzar booleano) y devolverlo en la reconstrucción.
- `cumplimiento`: nuevo evento `{t:'cumplimiento', k, v}` (los checks manuales presidente/firmantes/antelación) — persistir y reconstruir.
- proposiciones: asegurar que `objeciones` y la fecha de notificación base del 2060 se incluyan en el estado serializado.

- [ ] **Step 3: Mejorar la exportación a la hoja**

Sobre el inventario del Step 1, extender la hoja de resultados para que el acta/resumen exportado incluya, de forma legible:
- **Poderes con mandatario**: por cada poder, qué unidad y quién la representa (y un control de que ningún mandatario supere 5 propietarios, art. 25 h).
- **Proposiciones (art. 2060)**: por moción no firme, su estado (En circulación / Firme / Decaída), la fecha de cierre y la oposición acumulada.
- **Cumplimiento del reglamento**: la tabla de condiciones con su estado (de la Task 7).
Mantener las columnas existentes; solo agregar. No romper el formato que ya consumen hojas/fórmulas previas.

- [ ] **Step 4: Verificación manual (no hay test automatizado de Apps Script)**

Documentar en el commit que la verificación es manual: dos dispositivos con la misma URL de Apps Script ven el mismo mandatario, estado de proposición y checks de cumplimiento; y la hoja recibe las columnas nuevas. (Apps Script no se puede testear sin el entorno de Google; el dueño lo valida al desplegar.)

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes
git add apps/asamblea/Code.gs
git commit -m "Asamblea: Code.gs sincroniza y exporta mandatarios, proposiciones y cumplimiento"
```

---

## Task 6: Identidad visual (ui-ux-pro-max) + usabilidad responsive

**REQUIRED SUB-SKILL:** usar `ui-ux-pro-max` para esta tarea. Objetivo explícito del dueño: que **no parezca hecho por IA genérica** — identidad propia, con criterio, apropiada para una herramienta de asamblea de consorcio (seria e institucional pero moderna y confiable), no el look default de tarjetas grises.

**Files:**
- Modify: `apps/asamblea/make_votacion.py` (CSS y markup; es donde viven los estilos del generado)

- [ ] **Step 1: Fijar la dirección visual con ui-ux-pro-max**

Invocar `ui-ux-pro-max` para elegir, con criterio y de forma coherente: paleta (sobre la institucional actual `#1b2536`, sin volverla genérica), pareja tipográfica (ya usa Source Serif 4 para marca; definir el sistema completo display/texto/numérico tabular), escala de espaciado, radios, sombras, estados e interacciones (presente/poder/voto, tope lleno), y modo claro/oscuro. Dejar la decisión escrita (tokens) al principio del commit. Criterio rector: legibilidad a un brazo de distancia en el teléfono del moderador y personalidad sobria, no "dashboard de plantilla".

- [ ] **Step 2: Auditoría de usabilidad (anotar hallazgos)**

Abrir el HTML generado en viewport de teléfono (390px) y tablet (820px) y recorrer: Agenda, Votar (marcar presentes/poderes/votos), Reglamento, Proposiciones, Documentos. Anotar, por pantalla, problemas de heurísticas clave: visibilidad del estado (quórum/proposición de un vistazo), mínimos toques del moderador, foco visible, contraste de los estados de color (poder ámbar, tope lleno), targets táctiles ≥44px. Pegar la lista en el cuerpo del commit.

- [ ] **Step 3: Aplicar la identidad visual + los arreglos de usabilidad**

Implementar en `make_votacion.py` los tokens y ajustes definidos (CSS/markup). Preservar la base responsive existente (tabs sticky, inputs 16px, media queries) y toda la funcionalidad; es reestilizado con criterio, no reescritura estructural. Cada cambio: regenerar y revisar en los dos viewports y en claro/oscuro.

Incluir acá el pulido del **render del reglamento** (Minor diferidos de la Task 2): que `renderReglamento` maneje **listas** (`- `/`* ` → `<ul><li>`), **blockquotes** (`> ` → `<blockquote>`) y **separadores** (`---` → `<hr>`), porque el reglamento tiene incisos y notas que hoy se ven planos; ampliar el selector de `filtrarReglamento` a `li,blockquote` y **reaplicar el filtro al final de `renderReglamento`** (`filtrarReglamento($('#regBuscar').value)`) para que no se pierda ante un `renderAll`.

- [ ] **Step 4: Regenerar y verificación final**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && python3 make_votacion.py && node --test`
Expected: `ok` + todos los tests en verde (el reestilizado no debe tocar la lógica).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes
git add apps/asamblea/make_votacion.py
git commit -m "Asamblea: identidad visual propia (ui-ux-pro-max) y mejoras de usabilidad"
```

---

## Task 7: Panel de cumplimiento del reglamento (arriba en Votar)

Panel en vivo con las condiciones del reglamento aplicables a la asamblea, cada una con estado
**✓ se cumple / ✗ no se cumple / — pendiente** y la cita del artículo. Depende de la lógica de las
Tareas 1 (veredicto), 3 (poderes) y 4 (proposiciones). Condiciones: quórum (art. 25 e, auto),
mayoría por moción (art. 25 g, auto), tope de poderes (art. 25 h, auto), admin no vota (art. 25 c, auto),
presidente propietario + 2 firmantes (art. 25 c / punto 1, manual), antelación de convocatoria
(art. 25 a, manual). Se muestra arriba en la pestaña Votar.

**Files:**
- Modify: `apps/asamblea/logica.js` (+ tests): `mandatariosExcedidos`
- Modify: `apps/asamblea/make_votacion.py`: estado de checks manuales + UI del panel
- Modify: `apps/asamblea/Code.gs`: persistir los checks manuales

- [ ] **Step 1: Test de `mandatariosExcedidos` (falla)**

Agregar a `apps/asamblea/logica.test.mjs`:

```javascript
const { mandatariosExcedidos } = require('./logica.js');

test('lista los mandatarios que superan el tope de 5 propietarios', () => {
  const units = [];
  for (let uf = 1; uf <= 7; uf++) units.push({ uf, prop: 'P' + uf });
  units.push({ uf: 8, prop: 'MAND' });
  const poderes = {}; for (let uf = 1; uf <= 6; uf++) poderes[uf] = 'MAND'; // 6 propietarios
  assert.deepEqual(mandatariosExcedidos(poderes, units), ['MAND']);
});

test('sin excesos devuelve lista vacía', () => {
  const units = [{ uf: 1, prop: 'A' }, { uf: 2, prop: 'B' }, { uf: 3, prop: 'M' }];
  assert.deepEqual(mandatariosExcedidos({ 1: 'M', 2: 'M' }, units), []);
});
```

- [ ] **Step 2: Correr para verlo fallar**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && node --test`
Expected: FAIL (función no exportada).

- [ ] **Step 3: Implementar en `logica.js`**

Agregar dentro del IIFE (reusa `contarRepresentados` de la Task 3) y exponer en el `return`:

```javascript
  // Mandatarios que representan a MÁS de 5 propietarios (violan el art. 25 h).
  function mandatariosExcedidos(poderes, units){
    const mandatarios = new Set(Object.values(poderes).filter(Boolean));
    const out = [];
    for(const m of mandatarios){ if(contarRepresentados(m, poderes, units) > 5) out.push(m); }
    return out;
  }
```

- [ ] **Step 4: Correr — pasan**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && node --test`
Expected: PASS (todos).

- [ ] **Step 5: Estado de los checks manuales**

En `make_votacion.py`, extender el estado `fresh()` con un objeto `cumplimiento` para los checks manuales:
```javascript
cumplimiento: { presidentePropietario:null, dosFirmantes:null, antelacionOk:null }
```
(`null` = pendiente, `true`/`false` = lo marca el moderador). Propagarlo por `sync.send({t:'cumplimiento', k, v})` y aplicarlo en el receptor de sync, igual que los otros campos.

- [ ] **Step 6: UI del panel arriba en Votar**

En la cabecera de la vista Votar (≈ donde se renderiza `#quorum`), agregar un bloque `#cumplimiento` que liste cada condición con su estado y la cita del artículo. Automáticas, calculadas en cada render:
- **Quórum** (art. 25 e): `c.partPct > TOTAL_PCT/2` → ✓/✗.
- **Tope de poderes** (art. 25 h): `CTLogica.mandatariosExcedidos(S.poderes, UNITS).length===0` → ✓/✗ (si ✗, listar quién).
- **Admin no vota** (art. 25 c): ✓ salvo que una unidad con `admin:true` tenga voto en alguna moción → ✗.
- **Mayoría de la moción activa** (art. 25 g): usar el `verdict` de la moción activa → ✓ si aprobada / — si aún no.
Manuales (toggle del moderador, guardan en `S.cumplimiento`): **presidente propietario**, **2 firmantes del acta**, **antelación de convocatoria**. Cada ítem con ✓/✗/— y un `onclick` que cita el artículo vía `irAReglamento(...)` (función de la Task 2). Íconos claros y texto corto; en móvil, lista compacta.

- [ ] **Step 7: Persistir los checks manuales en `Code.gs`**

Agregar el manejo del evento `{t:'cumplimiento', k, v}` en `Code.gs` (análogo a los otros), para que los checks manuales se sincronicen entre dispositivos. Verificación manual (no hay test de Apps Script).

- [ ] **Step 8: Regenerar y verificar**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && python3 make_votacion.py && node --test`
Expected: `ok` + tests en verde. En el navegador (móvil): el panel muestra quórum/poderes/admin/mayoría automáticos y permite marcar los tres manuales; cada ítem cita su artículo.

- [ ] **Step 9: Commit**

```bash
cd /opt/consorcios-transparentes
git add apps/asamblea/logica.js apps/asamblea/logica.test.mjs apps/asamblea/make_votacion.py apps/asamblea/Code.gs
git commit -m "Asamblea: panel de cumplimiento del reglamento (quórum, poderes, mayorías, checks manuales)"
```

---

## Task 8: Normativa de referencia (pendiente de definir fuente)

Sumar a la app una sección de **normativa de referencia** aplicable, para consulta durante la asamblea y enlazable desde los puntos del orden del día:
- **LCT (Ley 20.744) arts. 252 y 253** — intimación a jubilarse del trabajador y trabajador jubilado (relevante al punto del encargado y su jubilación).
- **Propiedad horizontal — CCyC arts. 2037–2072** (régimen vigente; reemplazó a la Ley 13.512).
- **Encargados de edificios** — Estatuto (Ley 12.981) y CCT 589/10 (ya citado en el contenido de la asamblea).

**Decisiones (tomadas):**
1. **Fuente/alcance**: **resumen + enlace oficial** — por cada artículo/norma, un resumen claro (qué dice, para qué sirve en esta asamblea) + enlace a la fuente oficial (InfoLeg). NO transcribir texto legal completo de memoria; los resúmenes los verifica el dueño antes de publicar.
2. **Ubicación**: **pestaña propia "Normativa"** (separada del reglamento de copropiedad; agrupa LCT, PH y encargados). Coherente con que el panel/API ya separa `normativa` del `reglamento` (`api/app/routers/consorcio.py`).

Contenido (en `apps/asamblea/normativa.py` o similar, datos versionados): lista de ítems `{titulo, resumen, fuente_url}` con:
- **LCT (Ley 20.744) art. 252** — intimación a jubilarse: el empleador puede intimar al trabajador que reúne los requisitos para jubilarse, manteniendo la relación hasta que obtenga el beneficio o como máximo un año; cumplido el plazo, se extingue sin indemnización por antigüedad. Enlace InfoLeg.
- **LCT art. 253** — trabajador jubilado: reingreso/continuación; cómo se computa la antigüedad posterior. Enlace InfoLeg.
- **Propiedad horizontal — CCyC arts. 2037–2072** — régimen vigente (asambleas, mayorías, administrador, consejo). Enlace InfoLeg.
- **Encargados — Ley 12.981 (Estatuto)** y **CCT 589/10** — relación laboral del encargado, antigüedad e indemnización (ya citado en el contenido de la asamblea). Enlace oficial.

Implementación: patrón de la Task 2 — pestaña "Normativa" con la lista (tarjetas resumen + enlace), embebida por `make_votacion.py`. Enlazable desde los puntos del orden del día (p. ej. el del encargado → LCT 252/253) vía una función análoga a `irAReglamento`.

---

## Deploy (requiere confirmación del dueño; no lo ejecuta un subagente)

El deploy publica en `asamblea.neuralcore.dev` (Cloudflare Pages). Tras aprobar el resultado:

```bash
cd /opt/consorcios-transparentes/apps/asamblea
npx wrangler pages deploy pages-out --project-name <proyecto> --branch main
```
(Ver `apps/asamblea/deploy/LEEME.txt`. El contenido de la asamblea nueva se carga antes, en `asamblea_content.py`, cuando exista la convocatoria.)
