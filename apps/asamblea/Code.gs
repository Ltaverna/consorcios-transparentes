/**
 * Votación Consorcio Rivadavia 2069 - backend en Google Sheets.
 *
 * Cómo instalarlo (5 minutos):
 *  1. Creá una hoja de cálculo nueva en Google Sheets (por ejemplo "Votación Rivadavia 2069").
 *  2. Menú Extensiones → Apps Script. Borrá lo que haya y pegá este archivo completo. Guardá (ícono de disquete).
 *  3. Botón "Implementar" → "Nueva implementación" → tipo "Aplicación web".
 *       Ejecutar como: "Yo"       ·   Quién tiene acceso: "Cualquier persona"
 *     Autorizá los permisos cuando los pida (es tu propia hoja).
 *  4. Copiá la "URL de la aplicación web" (termina en /exec) y pegala en la app de votación, botón ⚙,
 *     campo "URL de la aplicación web". Poné un nombre al dispositivo y guardá.
 *
 * La hoja se llena sola con cuatro pestañas:
 *   Unidades       padrón con porcentual (lo manda la app la primera vez)
 *   Estado actual  una fila por unidad: presente, poder, voto de cada moción
 *   Resultados     resumen de quórum y de todas las mociones
 *   Moción 1, 2…   una pestaña por moción: resultado por opción y el voto de cada unidad
 *   Agenda         estado de cada punto, lista de oradores y respuestas de la administración
 *   Objeciones     objeciones de ausentes a las proposiciones (art. 2060)
 *   Historial      cada toque: fecha y hora, dispositivo, unidad, qué se marcó
 *
 * Varios teléfonos pueden usar la misma URL: todos ven y cargan lo mismo (se actualiza cada 4 segundos).
 */

const SHEET_ESTADO = 'Estado (no editar)';
const SHEET_UNIDADES = 'Unidades';
const SHEET_ACTUAL = 'Estado actual';
const SHEET_RESULT = 'Resultados';
const SHEET_HIST = 'Historial';

function doGet(e) {
  return json_({ ok: true, state: getState_() });
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const body = JSON.parse(e.postData.contents || '{}');
    const events = body.events || [];
    let state = getState_();
    const hist = [];
    for (const ev of events) {
      state = apply_(state, ev, hist);
    }
    state.ts = Date.now();
    saveState_(state);
    if (hist.length) appendHistory_(hist);
    rebuildTables_(state);
    rebuildAgenda_(state);
    return json_({ ok: true, state: state });
  } catch (err) {
    return json_({ ok: false, error: String(err), state: getState_() });
  } finally {
    lock.releaseLock();
  }
}

// ---------------------------------------------------------------- estado
function fresh_() {
  return { presentes: {}, poderes: {}, mociones: [], agenda: {}, palabra: [], respuestas: {}, objeciones: {}, ts: 0 };
}
function norm_(state) {
  state.agenda = state.agenda || {}; state.palabra = state.palabra || []; state.respuestas = state.respuestas || {}; state.objeciones = state.objeciones || {};
  return state;
}
function getState_() {
  const sh = sheet_(SHEET_ESTADO);
  const raw = sh.getRange('A1').getValue();
  if (!raw) return fresh_();
  try { return norm_(JSON.parse(raw)); } catch (e) { return fresh_(); }
}
function saveState_(state) {
  const sh = sheet_(SHEET_ESTADO);
  sh.getRange('A1').setValue(JSON.stringify(state));
  sh.getRange('B1').setValue(new Date());
}
function units_() {
  const sh = sheet_(SHEET_UNIDADES);
  const rows = sh.getDataRange().getValues();
  const out = [];
  for (let i = 1; i < rows.length; i++) if (rows[i][0] !== '') out.push({ uf: rows[i][0], piso: rows[i][1], prop: rows[i][2], tipo: rows[i][3], pct: Number(rows[i][4]) || 0 });
  return out;
}

// ---------------------------------------------------------------- eventos
function apply_(state, ev, hist) {
  const u = String(ev.uf);
  const when = new Date(ev.ts || Date.now());
  const dev = ev.dev || '';
  const unit = unitInfo_(ev.uf);
  switch (ev.t) {
    case 'init': {
      const sh = sheet_(SHEET_UNIDADES);
      if (sh.getLastRow() < 2 && ev.units && ev.units.length) {
        sh.clear();
        sh.getRange(1, 1, 1, 5).setValues([['UF', 'Piso-Depto', 'Propietario', 'Tipo', 'Porcentual (%)']]).setFontWeight('bold');
        sh.getRange(2, 1, ev.units.length, 5).setValues(ev.units);
        sh.setFrozenRows(1);
      }
      return state;
    }
    case 'presente':
      if (ev.v) { state.presentes[u] = true; delete state.poderes[u]; }
      else { delete state.presentes[u]; if (!state.poderes[u]) state.mociones.forEach(m => { delete m.votos[u]; }); }
      hist.push([when, dev, ev.v ? 'Presente' : 'Quita presencia', ev.uf, unit.piso, unit.prop, '']);
      return state;
    case 'poder':
      if (ev.v) { state.poderes[u] = ev.v; delete state.presentes[u]; }
      else { delete state.poderes[u]; if (!state.presentes[u]) state.mociones.forEach(m => { delete m.votos[u]; }); }
      hist.push([when, dev, ev.v ? 'Poder' : 'Quita poder', ev.uf, unit.piso, unit.prop, typeof ev.v === 'string' ? ev.v : '']);
      return state;
    case 'voto': {
      const m = state.mociones[ev.m];
      if (!m) return state;
      if (ev.v === null || ev.v === undefined) delete m.votos[u]; else m.votos[u] = ev.v;
      hist.push([when, dev, 'Voto · ' + m.titulo, ev.uf, unit.piso, unit.prop, ev.v == null ? '(borra voto)' : (m.opciones[ev.v] || ev.v)]);
      return state;
    }
    case 'mociones':
      state.mociones = ev.v || [];
      hist.push([when, dev, 'Configuración de mociones', '', '', '', state.mociones.map(m => m.titulo + ' [' + m.opciones.join(' / ') + ']').join(' | ')]);
      return state;
    case 'state':
      state = norm_({ presentes: ev.v.presentes || {}, poderes: ev.v.poderes || {}, mociones: ev.v.mociones || [], agenda: ev.v.agenda || state.agenda, palabra: state.palabra, respuestas: ev.v.respuestas || state.respuestas, objeciones: ev.v.objeciones || state.objeciones, ts: 0 });
      hist.push([when, dev, 'Carga completa de estado', '', '', '', '']);
      return state;
    case 'agenda': {
      const a = state.agenda[ev.id] || {};
      Object.assign(a, ev.v || {});
      state.agenda[ev.id] = a;
      hist.push([when, dev, 'Agenda · punto ' + ev.id, '', '', '', (ev.v && ev.v.estado) ? ev.v.estado : JSON.stringify(ev.v || {})]);
      return state;
    }
    case 'palabra': {
      const q = (state.palabra || []).filter(x => String(x.uf) !== u);
      if (ev.accion === 'pedir') q.push({ uf: ev.uf, nombre: ev.nombre || '', ts: ev.ts || Date.now() });
      state.palabra = q;
      hist.push([when, dev, ev.accion === 'pedir' ? 'Pide la palabra' : 'Sale de la lista de oradores', ev.uf, unit.piso, unit.prop, ev.nombre || '']);
      return state;
    }
    case 'respuesta':
      state.respuestas[ev.qid] = { texto: ev.texto || '', ts: ev.ts || Date.now(), dev: dev };
      hist.push([when, dev, 'Respuesta registrada · pregunta ' + ev.qid, '', '', '', (ev.texto || '').slice(0, 300)]);
      return state;
    case 'objecion': {
      const key = String(ev.m);
      state.objeciones[key] = state.objeciones[key] || {};
      if (ev.retira) { delete state.objeciones[key][u]; }
      else { state.objeciones[key][u] = { nombre: ev.nombre || '', motivo: ev.motivo || '', ts: ev.ts || Date.now() }; }
      hist.push([when, dev, (ev.retira ? 'Retira objeción' : 'OBJECIÓN') + ' · moción ' + (Number(ev.m) + 1), ev.uf, unit.piso, unit.prop, (ev.nombre || '') + (ev.motivo ? ' — ' + ev.motivo : '')]);
      appendObjecion_([when, Number(ev.m) + 1, (state.mociones[ev.m] || {}).titulo || '', ev.uf, unit.piso, unit.prop, ev.nombre || '', ev.motivo || '', ev.retira ? 'RETIRADA' : 'VIGENTE', dev]);
      return state;
    }
    case 'reset':
      hist.push([when, dev, 'REINICIO de la votación', '', '', '', '']);
      return fresh_();
    default:
      return state;
  }
}
function unitInfo_(uf) {
  const us = units_();
  for (const x of us) if (String(x.uf) === String(uf)) return x;
  return { piso: '', prop: '' };
}

// ---------------------------------------------------------------- hojas derivadas
const SHEET_AGENDA = 'Agenda';
const SHEET_OBJ = 'Objeciones';
function appendObjecion_(row) {
  const sh = sheet_(SHEET_OBJ);
  if (sh.getLastRow() === 0) {
    sh.getRange(1, 1, 1, 10).setValues([['Fecha y hora', 'N° moción', 'Moción', 'UF', 'Piso-Depto', 'Propietario', 'Nombre', 'Motivo', 'Estado', 'Dispositivo']]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  sh.getRange(sh.getLastRow() + 1, 1, 1, 10).setValues([row]);
}
function rebuildAgenda_(state) {
  const sh = sheet_(SHEET_AGENDA);
  sh.clear();
  const rows = [['Punto', 'Estado', 'Inicio', 'Fin', 'Nota / decisión']];
  Object.keys(state.agenda || {}).sort().forEach(id => { const a = state.agenda[id]; rows.push([id, a.estado || '', a.inicio ? new Date(a.inicio) : '', a.fin ? new Date(a.fin) : '', a.nota || '']); });
  rows.push(['', '', '', '', '']); rows.push(['Lista de oradores (orden)', 'UF', 'Nombre', 'Desde', '']);
  (state.palabra || []).forEach((p, i) => rows.push([i + 1, p.uf, p.nombre, new Date(p.ts), '']));
  rows.push(['', '', '', '', '']); rows.push(['Respuestas de la administración', 'Pregunta', 'Respuesta', 'Hora', 'Dispositivo']);
  Object.keys(state.respuestas || {}).forEach(k => { const r = state.respuestas[k]; rows.push(['', k, r.texto, new Date(r.ts), r.dev || '']); });
  sh.getRange(1, 1, rows.length, 5).setValues(rows);
  sh.getRange(1, 1, 1, 5).setFontWeight('bold');
}
function appendHistory_(rows) {
  const sh = sheet_(SHEET_HIST);
  if (sh.getLastRow() === 0) {
    sh.getRange(1, 1, 1, 7).setValues([['Fecha y hora', 'Dispositivo', 'Acción', 'UF', 'Piso-Depto', 'Propietario', 'Detalle']]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  sh.getRange(sh.getLastRow() + 1, 1, rows.length, 7).setValues(rows);
}
function rebuildTables_(state) {
  const us = units_();
  if (!us.length) return;
  const mocs = state.mociones || [];
  // ---- Estado actual
  const sh = sheet_(SHEET_ACTUAL);
  sh.clear();
  const head = ['UF', 'Piso-Depto', 'Propietario', 'Porcentual (%)', 'Presente', 'Poder'].concat(mocs.map(m => m.titulo));
  const rows = us.map(u => {
    const k = String(u.uf);
    const pres = !!state.presentes[k], pod = state.poderes[k];
    return [u.uf, u.piso, u.prop, u.pct, pres ? 'SI' : '', pod ? (typeof pod === 'string' ? pod : 'SI') : ''].concat(mocs.map(m => (m.votos[k] == null ? '' : (m.opciones[m.votos[k]] || ''))));
  });
  sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold');
  if (rows.length) sh.getRange(2, 1, rows.length, head.length).setValues(rows);
  sh.setFrozenRows(1);
  // ---- Resultados
  const total = us.reduce((s, u) => s + u.pct, 0);
  let presN = 0, presPct = 0, podN = 0, podPct = 0;
  us.forEach(u => { const k = String(u.uf); if (state.presentes[k]) { presN++; presPct += u.pct; } else if (state.poderes[k]) { podN++; podPct += u.pct; } });
  const out = [['Actualizado', new Date(), '', ''], ['Total porcentual del edificio', total, '', ''], ['Unidades presentes', presN, presPct, ''], ['Unidades por poder', podN, podPct, ''], ['Quórum (unidades / porcentual)', presN + podN, presPct + podPct, ''], ['', '', '', '']];
  mocs.forEach(m => {
    out.push(['MOCIÓN: ' + m.titulo, 'Unidades', 'Porcentual (%)', '% de presentes']);
    m.opciones.forEach((o, i) => {
      let n = 0, p = 0;
      us.forEach(u => { const k = String(u.uf); if ((state.presentes[k] || state.poderes[k]) && m.votos[k] === i) { n++; p += u.pct; } });
      out.push([o, n, p, (presPct + podPct) ? p / (presPct + podPct) * 100 : 0]);
    });
    out.push(['', '', '', '']);
  });
  const sr = sheet_(SHEET_RESULT);
  sr.clear();
  sr.getRange(1, 1, out.length, 4).setValues(out);
  sr.getRange(1, 1, 1, 4).setFontWeight('bold');
  // ---- una pestaña por moción
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const keep = {};
  mocs.forEach((m, k) => {
    const name = mocionSheetName_(k, m.titulo);
    keep[name] = true;
    const sm = sheet_(name);
    sm.clear();
    const block = [['MOCIÓN ' + (k + 1) + ': ' + m.titulo, '', '', ''], ['Actualizado', new Date(), '', ''], ['Regla', { abs: 'mayoría absoluta del total', pres: 'mayoría simple de presentes', '2/3': 'dos tercios del total' }[m.regla] || m.regla, '', ''], ['', '', '', ''], ['Opción', 'Unidades', 'Porcentual (%)', '% de presentes']];
    m.opciones.forEach((o, i) => {
      let n = 0, p = 0;
      us.forEach(u => { const kk = String(u.uf); if ((state.presentes[kk] || state.poderes[kk]) && m.votos[kk] === i) { n++; p += u.pct; } });
      block.push([o, n, p, (presPct + podPct) ? p / (presPct + podPct) * 100 : 0]);
    });
    let sinVotar = 0;
    us.forEach(u => { const kk = String(u.uf); if ((state.presentes[kk] || state.poderes[kk]) && m.votos[kk] == null) sinVotar++; });
    block.push(['Presentes sin votar', sinVotar, '', '']);
    block.push(['', '', '', '']);
    block.push(['UF', 'Piso-Depto', 'Propietario', 'Porcentual (%)', 'Presente / poder', 'Voto']);
    us.forEach(u => {
      const kk = String(u.uf);
      const pres = state.presentes[kk] ? 'Presente' : (state.poderes[kk] ? ('Poder' + (typeof state.poderes[kk] === 'string' ? ' (' + state.poderes[kk] + ')' : '')) : '');
      block.push([u.uf, u.piso, u.prop, u.pct, pres, m.votos[kk] == null ? '' : (m.opciones[m.votos[kk]] || '')]);
    });
    const width = 6;
    const rows = block.map(r => { while (r.length < width) r.push(''); return r.slice(0, width); });
    sm.getRange(1, 1, rows.length, width).setValues(rows);
    sm.getRange(1, 1, 1, width).setFontWeight('bold');
    sm.getRange(5, 1, 1, width).setFontWeight('bold');
    sm.getRange(m.opciones.length + 8, 1, 1, width).setFontWeight('bold');
  });
  ss.getSheets().forEach(sh => { const n = sh.getName(); if (/^Moción \d+/.test(n) && !keep[n]) ss.deleteSheet(sh); });
}
function mocionSheetName_(k, titulo) {
  const t = String(titulo || '').replace(/[\[\]\*\/\\?:]/g, ' ').trim();
  return ('Moción ' + (k + 1) + ' - ' + t).slice(0, 60);
}

// ---------------------------------------------------------------- utilidades
function sheet_(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  return ss.getSheetByName(name) || ss.insertSheet(name);
}
function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
