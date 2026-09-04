import os
HERE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(HERE, "datos") + "/"
PRIVADO = os.environ.get("CT_PRIVADO", os.path.expanduser("~/consorcio-transparente-privado")) + "/"
import json, re
SC = os.path.join(HERE, "..", "..", "apps", "asamblea") + "/"
p = SC + "make_votacion.py"; s = open(p).read()
assert "asamblea_content" not in s, "ya parcheado"

# ---------------------------------------------------------------- data injection
s = s.replace('UNITS = json.load(open(SC + "votacion_units.json"))',
 'UNITS = json.load(open(SC + "votacion_units.json"))\nfrom asamblea_content import AGENDA, PREGUNTAS, CONVOCATORIA, PODER\nCONTENT = json.dumps(dict(agenda=AGENDA, preguntas=PREGUNTAS, convocatoria=CONVOCATORIA, poder=PODER), ensure_ascii=False).replace("</", "<\\\\/")')
s = s.replace('<script id="data" type="application/json">__DATA__</script>',
 '<script id="data" type="application/json">__DATA__</script>\n<script id="content" type="application/json">__CONTENT__</script>')
s = s.replace('out = HTML.replace("__DATA__", DATA)', 'out = HTML.replace("__DATA__", DATA).replace("__CONTENT__", CONTENT)')
s = s.replace("<title>Votación Rivadavia 2069</title>", "<title>Asamblea Rivadavia 2069</title>")
s = s.replace('<meta name="apple-mobile-web-app-title" content="Votación 2069">', '<meta name="apple-mobile-web-app-title" content="Asamblea 2069">')
s = s.replace('<div><h1>Votación Rivadavia 2069</h1>', '<div><h1>Votar</h1>')

# ---------------------------------------------------------------- CSS
css = r"""
/* ---- pestañas y vistas */
.tabs{position:sticky;top:0;z-index:12;background:var(--ink);color:var(--surface);display:flex;align-items:stretch;gap:0;overflow-x:auto;scrollbar-width:none;padding:0 6px}
.tabs button{flex:1 0 auto;min-width:64px;padding:12px 10px 10px;font-size:13px;font-weight:600;color:rgba(255,255,255,.72);border-bottom:3px solid transparent;white-space:nowrap;transition:color .15s ease,border-color .15s ease}
.tabs button[aria-selected="true"]{color:#fff;border-bottom-color:#fff}
.tabs .brand{flex:0 0 auto;align-self:center;font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:15px;padding:0 10px 0 6px;color:#fff;white-space:nowrap}
.top{top:46px}
.view{display:grid;gap:14px;padding:14px 0 24px}
.view h2.sec{font-family:"Source Serif 4",Georgia,serif;font-size:22px;letter-spacing:-.01em;text-transform:none;color:var(--ink)}
.lead{color:var(--ink-2);font-size:15px;max-width:70ch}
.card{background:var(--surface);border:1px solid var(--hair);border-radius:12px;padding:14px 16px;display:grid;gap:10px}
.card h3{margin:0;font-size:17px;line-height:1.3}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:3px 9px;border-radius:999px;background:var(--surface-2);color:var(--ink-2)}
.pill.curso{background:var(--warn-soft);color:#7a5200} .pill.tratado{background:var(--good-soft);color:#0b6a0b} .pill.pend{background:var(--surface-2)}
.pt-head{display:flex;gap:10px;align-items:flex-start;justify-content:space-between}
.pt-num{font-family:"Source Serif 4",Georgia,serif;font-size:28px;font-weight:600;color:var(--muted);line-height:1;min-width:34px}
.kv{display:grid;gap:4px;font-size:14.5px} .kv b{color:var(--ink)} .kv p{color:var(--ink-2)}
.moc-res{display:grid;gap:6px;border-top:1px solid var(--hair-2);padding-top:10px}
.moc-res .row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;font-size:14px;align-items:center}
.moc-res .row i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:6px}
.moc-res .bar{height:6px;border-radius:3px;background:var(--hair-2);overflow:hidden}.moc-res .bar b{display:block;height:100%}
.actions{display:flex;gap:8px;flex-wrap:wrap}
.btn.sm{padding:8px 12px;font-size:13.5px;min-height:40px}
.modbar{display:flex;align-items:center;justify-content:space-between;gap:10px;background:var(--surface-2);border:1px dashed var(--hair);border-radius:10px;padding:10px 12px;font-size:14px}
.modbar b{color:var(--ink)}
.mod-only{display:none} body.mod .mod-only{display:initial} body.mod .mod-only.actions,body.mod .mod-only.row{display:flex}
.oradores{display:grid;gap:6px} .orador{display:flex;justify-content:space-between;align-items:center;gap:10px;background:var(--surface-2);border-radius:8px;padding:8px 12px;font-size:15px}
.orador .n{font-weight:700;color:var(--muted);min-width:22px}
.q{display:grid;gap:8px} .q .tema{font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.q p.txt{font-size:15.5px;line-height:1.45;color:var(--ink)} .q .doc{font-size:13px;color:var(--ink-2);padding:8px 10px;background:var(--surface-2);border-radius:8px}
.q .resp{border-left:3px solid var(--good);padding:6px 10px;font-size:14.5px;background:var(--good-soft);border-radius:0 8px 8px 0}
.q textarea{width:100%;min-height:70px;font:inherit;font-size:16px;border:1px solid var(--hair);border-radius:8px;padding:10px;background:var(--surface);color:var(--ink)}
.prop{display:grid;gap:8px}
.prop .stat{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}
.prop .stat div{background:var(--surface-2);border-radius:8px;padding:8px 10px;font-size:13px;color:var(--ink-2)} .prop .stat b{display:block;font-size:20px;color:var(--ink);font-weight:700}
.form{display:grid;gap:8px} .form label{display:grid;gap:4px;font-size:13.5px;color:var(--ink-2);font-weight:500}
.form input,.form select,.form textarea{font:inherit;font-size:16px;padding:10px 12px;border:1px solid var(--hair);border-radius:8px;background:var(--surface);color:var(--ink);width:100%}
.objlist{display:grid;gap:6px} .obj{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;background:var(--surface-2);border-radius:8px;padding:8px 12px;font-size:14px}
.docs a{color:var(--accent-ink);font-weight:600}
pre.doc{white-space:pre-wrap;font:inherit;font-size:14.5px;line-height:1.5;color:var(--ink-2);margin:0}
.vhide{display:none!important}
@media (max-width:640px){ .tabs button{font-size:12.5px;padding:12px 8px 10px;min-width:56px} .tabs .brand{display:none} .view h2.sec{font-size:20px} }
"""
s = s.replace("/* ---- bottom bar */", css + "\n/* ---- bottom bar */")

# ---------------------------------------------------------------- HTML: tabs + views
tabs = '''<nav class="tabs" role="tablist" aria-label="Secciones">
  <span class="brand">Rivadavia 2069</span>
  <button role="tab" data-tab="agenda" aria-selected="true">Agenda</button>
  <button role="tab" data-tab="votar" aria-selected="false">Votar</button>
  <button role="tab" data-tab="preguntas" aria-selected="false">Preguntas</button>
  <button role="tab" data-tab="propos" aria-selected="false">Proposiciones</button>
  <button role="tab" data-tab="docs" aria-selected="false">Documentos</button>
</nav>
'''
s = s.replace('<div class="top" id="top">', tabs + '<div class="top" id="top">', 1)
# wrap votar body
s = s.replace('<div class="wrap">\n  <div class="toolbar">', '<div class="wrap" id="votarWrap">\n  <div class="toolbar">', 1)
views = '''
<div class="wrap view" id="view-agenda">
  <div class="modbar" id="modbar"></div>
  <h2 class="sec">Asamblea extraordinaria · 3 de septiembre de 2026, 19:00</h2>
  <p class="lead">Seis puntos del orden del día. En cada uno: qué hay que decidir, qué conviene pedir, y la moción con su resultado en vivo. Tocá "Pedir la palabra" para anotarte en la lista de oradores.</p>
  <div class="card" id="quorumCard"></div>
  <div class="card"><h3>Lista de oradores</h3><div class="oradores" id="oradores"></div><div class="actions"><button class="btn primary sm" id="btnPalabra">Pedir la palabra</button></div></div>
  <div id="agendaList" style="display:grid;gap:12px"></div>
</div>
<div class="wrap view" id="view-preguntas">
  <h2 class="sec">Preguntas a la administración</h2>
  <p class="lead">Surgen de las liquidaciones de julio y agosto 2026 y de los 150 comprobantes cargados en Redconar. Cada pregunta cita el documento exacto; los comprobantes se ven en Redconar → Mi cuenta → Gastos y comprobantes. Las respuestas que dé la administración quedan registradas.</p>
  <div id="preguntasList" style="display:grid;gap:12px"></div>
</div>
<div class="wrap view" id="view-propos">
  <h2 class="sec">Proposiciones y objeciones</h2>
  <p class="lead" id="proposLead"></p>
  <div id="proposList" style="display:grid;gap:12px"></div>
</div>
<div class="wrap view" id="view-docs">
  <h2 class="sec">Documentos</h2>
  <div class="card docs"><h3>Informe de expensas (julio y agosto 2026)</h3><p class="lead">Gastos, proveedores, deudores, flujo de fondos, hallazgos y comprobantes verificados.</p><div class="actions"><a class="btn primary sm" href="/informe-expensas.html" target="_blank" rel="noopener">Abrir informe</a><a class="btn sm" href="/analisis-expensas.xlsx">Descargar Excel</a></div></div>
  <div class="card docs"><h3>Convocatoria</h3><pre class="doc" id="docConv"></pre></div>
  <div class="card docs"><h3>Modelo de poder</h3><pre class="doc" id="docPoder"></pre></div>
  <div class="card docs"><h3>Cómo se usa esta app</h3><pre class="doc">Agenda: seguí el punto en tratamiento y anotate para hablar.
Votar: el moderador marca presentes, poderes y votos; todos ven el resultado en vivo con la doble mayoría (unidades y porcentual).
Preguntas: las preguntas a la administración con su documento de respaldo y la respuesta registrada.
Proposiciones: si no hubo 50 % + 1, lo votado es proposición; los ausentes pueden objetar hasta el 18/09/2026.
Documentos: informe, convocatoria y poder.
Modo moderador (PIN): en Agenda, botón "Soy moderador".</pre></div>
</div>
<dialog id="dlgPin"><form method="dialog" class="body"><h3>Modo moderador</h3><label>PIN <input id="pinInput" type="password" inputmode="numeric" autocomplete="off" placeholder="PIN"></label><p class="note">Habilita marcar presencia y votos, cambiar el punto en tratamiento, dar la palabra y registrar respuestas.</p><div class="row"><button class="btn" value="cancel">Cancelar</button><button class="btn primary" id="pinOk" value="ok">Entrar</button></div></form></dialog>
<dialog id="dlgPalabra"><div class="body"><h3>Pedir la palabra</h3><div class="form"><label>Unidad <select id="palUf"></select></label><label>Nombre <input id="palNombre" placeholder="Nombre y apellido" autocomplete="name"></label></div><div class="row"><button class="btn" id="palCancel">Cancelar</button><button class="btn primary" id="palOk">Anotarme</button></div></div></dialog>
<dialog id="dlgObj"><div class="body"><h3>Registrar objeción</h3><p class="note" id="objTitulo"></p><div class="form"><label>Unidad <select id="objUf"></select></label><label>Nombre <input id="objNombre" placeholder="Nombre y apellido" autocomplete="name"></label><label>Motivo (opcional) <textarea id="objMotivo" rows="3"></textarea></label></div><div class="row"><button class="btn" id="objCancel">Cancelar</button><button class="btn primary" id="objOk">Objetar</button></div></div></dialog>
'''
s = s.replace('<div class="bottom"><div class="wrap">', views + '\n<div class="bottom"><div class="wrap">', 1)

# ---------------------------------------------------------------- JS
js = r"""
// ================= asamblea: pestañas, moderador, agenda, preguntas, proposiciones
const C = JSON.parse(document.getElementById('content').textContent);
const PIN = '2069';
const DEADLINE = new Date(2026, 8, 18, 23, 59);
let MOD = false; try{ MOD = localStorage.getItem(KEY+'-mod')==='1'; }catch(e){}
function setMod(v){ MOD=v; try{ localStorage.setItem(KEY+'-mod', v?'1':'0'); }catch(e){} document.body.classList.toggle('mod', v); renderAll(); }
document.body.classList.toggle('mod', MOD);
function needMod(){ if(MOD) return true; $('#pinInput').value=''; $('#dlgPin').showModal(); return false; }
$('#pinOk').addEventListener('click', e=>{ if($('#pinInput').value.trim()===PIN){ setMod(true); toast('Modo moderador activado'); } else { e.preventDefault(); $('#pinInput').value=''; $('#pinInput').placeholder='PIN incorrecto'; } });

let TAB = 'agenda';
function setTab(t){ TAB=t; document.querySelectorAll('.tabs button').forEach(b=>b.setAttribute('aria-selected', String(b.dataset.tab===t)));
  const votar = t==='votar'; $('#top').classList.toggle('vhide', !votar); $('#votarWrap').classList.toggle('vhide', !votar); document.querySelector('.bottom').classList.toggle('vhide', !votar);
  ['agenda','preguntas','propos','docs'].forEach(v=>$('#view-'+v).classList.toggle('vhide', t!==v));
  window.scrollTo(0,0); renderAll(); try{ localStorage.setItem(KEY+'-tab', t); }catch(e){} }
document.querySelector('.tabs').addEventListener('click', e=>{ const b=e.target.closest('button[data-tab]'); if(b) setTab(b.dataset.tab); });

// gate marking to moderator
const _listClick = $('#list');
_listClick.addEventListener('click', e=>{ if(!MOD && e.target.closest('button[data-act]')){ e.stopImmediatePropagation(); needMod(); } }, true);
$('#roll').addEventListener('click', e=>{ if(!MOD && e.target.closest('button[data-act]')){ e.stopImmediatePropagation(); needMod(); } }, true);
['btnPresentes','btnPlanilla','btnReset','btnSettings','btnSettings2'].forEach(id=>{ const el=$('#'+id); if(el) el.addEventListener('click', e=>{ if(!MOD){ e.stopImmediatePropagation(); $('#dlgMas').close(); needMod(); } }, true); });

// ---- helpers
const A = ()=>S.agenda||(S.agenda={}); const PAL = ()=>S.palabra||(S.palabra=[]); const RESP = ()=>S.respuestas||(S.respuestas={}); const OBJ = ()=>S.objeciones||(S.objeciones={});
const hhmm = ts => ts? new Date(ts).toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'}) : '';
function mocIndexByTitle(t){ return S.mociones.findIndex(m=>m.titulo===t); }
function quorumInfo(){ const c=compute(S.mociones[0]||{opciones:[],votos:{},regla:'abs'}); const firm = c.partN > N/2 && c.partPct > TOTAL_PCT/2; return Object.assign(c,{firm}); }
function uf(u){ return UNITS.find(x=>x.uf===+u); }
function ufOptions(sel, filter){ const list = UNITS.filter(filter||(()=>true)); sel.innerHTML = '<option value="">Elegí tu unidad…</option>' + list.map(u=>`<option value="${u.uf}">${esc(u.piso)} · ${esc(u.prop)}</option>`).join(''); }

// ---- agenda
function renderAgenda(){
  const q=quorumInfo();
  $('#modbar').innerHTML = MOD ? `<span><b>Modo moderador</b> activo en este dispositivo</span><button class="btn sm" id="btnModOff">Salir</button>` : `<span>Ves la asamblea en vivo. Para marcar presencia, votos y agenda:</span><button class="btn primary sm" id="btnModOn">Soy moderador</button>`;
  $('#quorumCard').innerHTML = `<h3>Quórum</h3><div class="prop"><div class="stat"><div>Presentes<b>${q.presN}</b></div><div>Con poder<b>${q.poderN}</b></div><div>Unidades<b>${q.partN} / ${N}</b></div><div>Porcentual<b>${fp(q.partPct)}</b></div></div>
    <div class="note">${q.firm ? '<b style="color:var(--good)">Hay 50 % + 1 del total: las decisiones son firmes.</b>' : 'Sin 50 % + 1 del total (59 unidades y más de 49,96 %): lo votado queda como <b>proposición</b> y se circula 15 días (art. 2060).'}</div></div>`;
  const pal = PAL();
  $('#oradores').innerHTML = pal.length ? pal.map((p,i)=>{ const u=uf(p.uf)||{}; return `<div class="orador"><span><span class="n">${i+1}</span> ${esc(u.piso||'')} · ${esc(p.nombre||u.prop||'')}</span>${MOD?`<button class="btn sm" data-pal-done="${p.uf}">Ya habló</button>`:''}</div>`; }).join('') : '<div class="note">Nadie anotado todavía.</div>';
  $('#agendaList').innerHTML = C.agenda.map(pt=>{ const a=A()[pt.id]||{}; const est=a.estado||'pendiente'; const mi = pt.mocion? mocIndexByTitle(pt.mocion) : -1;
    let moc=''; if(pt.mocion){ if(mi>=0){ const m=S.mociones[mi]; const c=compute(m); moc = `<div class="moc-res"><div class="row"><b>Moción: ${esc(m.titulo)}</b><span class="note">${c.opts.reduce((s,o)=>s+o.n,0)} votos</span><span></span></div>` + c.opts.map(o=>{ const v=verdict(m,c,o); return `<div class="row"><span><i style="background:var(--${COLORS[o.i%4]})"></i>${esc(o.name)}</span><b class="num">${fp(o.pct)}</b><span class="note num">${o.n} UF${v&&v.ok?' · <b style="color:var(--good)">aprobada</b>':''}</span></div><div class="bar"><b style="width:${(o.pct/TOTAL_PCT*100).toFixed(2)}%;background:var(--${COLORS[o.i%4]})"></b></div>`; }).join('') + `<div class="actions"><button class="btn sm" data-goto-moc="${mi}">Ir a votar esta moción</button></div></div>`; } else { moc = `<div class="moc-res"><span class="note">Moción prevista: <b>${esc(pt.mocion)}</b> (todavía no creada)</span><div class="actions mod-only"><button class="btn sm" data-create-moc="${esc(pt.mocion)}">Crear moción</button></div></div>`; } }
    return `<div class="card" data-pt="${pt.id}"><div class="pt-head"><div style="display:flex;gap:12px;align-items:flex-start"><span class="pt-num">${pt.id}</span><div><h3>${esc(pt.titulo)}</h3><div class="note">${est==='curso'?'En tratamiento desde '+hhmm(a.inicio):est==='tratado'?'Tratado '+hhmm(a.inicio)+(a.fin?' a '+hhmm(a.fin):''):'Pendiente'}</div></div></div><span class="pill ${est==='curso'?'curso':est==='tratado'?'tratado':'pend'}">${est==='curso'?'En curso':est==='tratado'?'Tratado':'Pendiente'}</span></div>
      <div class="kv"><b>Qué se decide</b><p>${esc(pt.decidir)}</p><b>Qué conviene pedir</b><p>${esc(pt.guia)}</p>${a.nota?`<b>Decisión / nota del acta</b><p>${esc(a.nota)}</p>`:''}</div>${moc}
      <div class="actions mod-only">${est!=='curso'?`<button class="btn primary sm" data-pt-act="curso">Iniciar tratamiento</button>`:`<button class="btn primary sm" data-pt-act="tratado">Cerrar punto</button>`}<button class="btn sm" data-pt-act="nota">Anotar decisión</button>${est!=='pendiente'?`<button class="btn sm" data-pt-act="pendiente">Volver a pendiente</button>`:''}</div></div>`; }).join('');
}
$('#view-agenda').addEventListener('click', e=>{
  const b=e.target.closest('button'); if(!b) return;
  if(b.id==='btnModOn') return needMod(); if(b.id==='btnModOff'){ setMod(false); return; }
  if(b.dataset.palDone){ if(!needMod()) return; sync.send({t:'palabra', uf:+b.dataset.palDone, accion:'quitar'}); S.palabra=PAL().filter(p=>String(p.uf)!==b.dataset.palDone); save(); renderAll(); return; }
  if(b.dataset.gotoMoc!=null){ S.activa=+b.dataset.gotoMoc; save(); setTab('votar'); return; }
  if(b.dataset.createMoc){ if(!needMod()) return; S.mociones.push({titulo:b.dataset.createMoc, opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{}}); save(); sync.send({t:'mociones', v:S.mociones}); renderAll(); return; }
  const card=b.closest('[data-pt]'); if(card && b.dataset.ptAct){ if(!needMod()) return; const id=card.dataset.pt; const a=A()[id]||{}; const act=b.dataset.ptAct; let v={};
    if(act==='curso'){ Object.keys(A()).forEach(k=>{ if(A()[k].estado==='curso'){ A()[k].estado='tratado'; A()[k].fin=Date.now(); sync.send({t:'agenda', id:k, v:{estado:'tratado', fin:A()[k].fin}}); } }); v={estado:'curso', inicio:Date.now()}; }
    else if(act==='tratado'){ v={estado:'tratado', fin:Date.now()}; }
    else if(act==='pendiente'){ v={estado:'pendiente'}; }
    else if(act==='nota'){ const t=prompt('Decisión o nota para el acta (punto '+id+'):', a.nota||''); if(t===null) return; v={nota:t}; }
    A()[id]=Object.assign(a, v); save(); sync.send({t:'agenda', id, v}); renderAll(); }
});
$('#btnPalabra').addEventListener('click', ()=>{ ufOptions($('#palUf')); $('#palNombre').value=''; $('#dlgPalabra').showModal(); });
$('#palCancel').addEventListener('click', ()=>$('#dlgPalabra').close());
$('#palOk').addEventListener('click', ()=>{ const u=+$('#palUf').value; if(!u){ toast('Elegí tu unidad'); return; } const nombre=$('#palNombre').value.trim(); S.palabra=PAL().filter(p=>p.uf!==u).concat([{uf:u, nombre, ts:Date.now()}]); save(); sync.send({t:'palabra', uf:u, accion:'pedir', nombre}); $('#dlgPalabra').close(); renderAll(); toast('Anotado en la lista de oradores'); });

// ---- preguntas
function renderPreguntas(){
  $('#preguntasList').innerHTML = C.preguntas.map((q,i)=>{ const r=RESP()[q.id]; return `<div class="card q" data-q="${q.id}"><span class="tema">${i+1} · ${esc(q.tema)}${q.monto?` · ${fmt.format(q.monto)}`:''}</span><p class="txt">${esc(q.pregunta)}</p><div class="doc">Documento: ${esc(q.doc)}</div>
    ${r&&r.texto?`<div class="resp"><b>Respuesta de la administración</b> (${hhmm(r.ts)}): ${esc(r.texto)}</div>`:'<div class="note">Sin respuesta registrada.</div>'}
    <div class="mod-only actions"><button class="btn sm" data-resp="${q.id}">${r&&r.texto?'Editar respuesta':'Registrar respuesta'}</button></div></div>`; }).join('');
}
$('#view-preguntas').addEventListener('click', e=>{ const b=e.target.closest('button[data-resp]'); if(!b) return; if(!needMod()) return; const id=b.dataset.resp; const cur=(RESP()[id]||{}).texto||''; const t=prompt('Respuesta dada por la administración:', cur); if(t===null) return; RESP()[id]={texto:t, ts:Date.now()}; save(); sync.send({t:'respuesta', qid:id, texto:t}); renderAll(); });

// ---- proposiciones
function renderPropos(){
  const q=quorumInfo(); const ausentes = UNITS.filter(u=>!participa(u)); const ausN=ausentes.length, ausPct=ausentes.reduce((s,u)=>s+u.pct,0);
  $('#proposLead').innerHTML = q.firm ? `Hubo ${q.partN} unidades y ${fp(q.partPct)} del porcentual: <b>se alcanzó el 50 % + 1 del total</b>, las decisiones son firmes y no corresponde el régimen de proposiciones.` :
    `Quórum: ${q.partN} unidades y ${fp(q.partPct)}. <b>No se alcanzó el 50 % + 1 del total</b>, así que cada moción votada es una proposición (art. 2060 CCyC). Los propietarios ausentes (${ausN} unidades, ${fp(ausPct)}) pueden objetarla hasta el <b>${DEADLINE.toLocaleDateString('es-AR')}</b>. Criterio de esta app: la proposición queda objetada si las objeciones alcanzan la mayoría de los ausentes en unidades y en porcentual.`;
  $('#proposList').innerHTML = S.mociones.map((m,i)=>{ const c=compute(m); const win=c.opts.filter(o=>!o.abst).sort((a,b)=>b.pct-a.pct)[0]; const objs=OBJ()[i]||{}; const oe=Object.keys(objs).map(k=>({uf:+k, ...objs[k]})).filter(o=>uf(o.uf)); const oN=oe.length, oPct=oe.reduce((s,o)=>s+uf(o.uf).pct,0);
    const votada = c.opts.reduce((s,o)=>s+o.n,0)>0; const objetada = !q.firm && ausN>0 && oN > ausN/2 && oPct > ausPct/2; const vencida = Date.now()>DEADLINE.getTime();
    const estado = !votada ? 'Sin votar todavía' : q.firm ? 'Decisión firme' : objetada ? 'Objetada por los ausentes' : vencida ? 'Proposición firme (venció el plazo)' : 'Proposición en circulación';
    return `<div class="card prop"><h3>Moción ${i+1}: ${esc(m.titulo)}</h3><span class="pill ${objetada?'':votada?(q.firm||vencida?'tratado':'curso'):'pend'}">${estado}</span>
      ${votada?`<div class="note">Resultado: ${c.opts.map(o=>`${esc(o.name)} ${fp(o.pct)} (${o.n} UF)`).join(' · ')}${win?` → mayoría: <b>${esc(win.name)}</b>`:''}</div>`:''}
      ${!q.firm&&votada?`<div class="stat"><div>Objeciones<b>${oN}</b></div><div>Porcentual objetante<b>${fp(oPct)}</b></div><div>Ausentes<b>${ausN} · ${fp(ausPct)}</b></div><div>Vence<b style="font-size:15px">${DEADLINE.toLocaleDateString('es-AR')}</b></div></div>
      <div class="objlist">${oe.length?oe.map(o=>`<div class="obj"><b>${esc(uf(o.uf).piso)}</b><span>${esc(o.nombre||uf(o.uf).prop)}${o.motivo?` — <i>${esc(o.motivo)}</i>`:''}</span><span class="note">${new Date(o.ts).toLocaleDateString('es-AR')}</span></div>`).join(''):'<div class="note">Sin objeciones registradas.</div>'}</div>
      <div class="actions">${vencida?'':`<button class="btn primary sm" data-obj="${i}">Registrar objeción</button>`}</div>`:''}</div>`; }).join('') || '<div class="note">Todavía no hay mociones.</div>';
}
$('#view-propos').addEventListener('click', e=>{ const b=e.target.closest('button[data-obj]'); if(!b) return; const i=+b.dataset.obj; $('#objTitulo').textContent='Moción '+(i+1)+': '+S.mociones[i].titulo; ufOptions($('#objUf'), u=>!participa(u)); $('#objNombre').value=''; $('#objMotivo').value=''; $('#dlgObj').dataset.m=i; $('#dlgObj').showModal(); });
$('#objCancel').addEventListener('click', ()=>$('#dlgObj').close());
$('#objOk').addEventListener('click', ()=>{ const i=+$('#dlgObj').dataset.m; const u=+$('#objUf').value; if(!u){ toast('Elegí tu unidad'); return; } const nombre=$('#objNombre').value.trim(); if(!nombre){ toast('Escribí tu nombre'); return; } const motivo=$('#objMotivo').value.trim(); OBJ()[i]=OBJ()[i]||{}; OBJ()[i][u]={nombre, motivo, ts:Date.now()}; save(); sync.send({t:'objecion', m:i, uf:u, nombre, motivo}); $('#dlgObj').close(); renderAll(); toast('Objeción registrada'); });

// ---- documentos
$('#docConv').textContent = C.convocatoria; $('#docPoder').textContent = C.poder;

// ---- acta ampliada
const _buildPrint = buildPrint;
buildPrint = function(){ _buildPrint(); const q=quorumInfo(); let h='';
  h+=`<h2>Orden del día</h2><table><tr><th>#</th><th>Punto</th><th>Estado</th><th>Decisión / nota</th></tr>${C.agenda.map(pt=>{ const a=A()[pt.id]||{}; return `<tr><td>${pt.id}</td><td>${esc(pt.titulo)}</td><td>${a.estado==='tratado'?'Tratado':a.estado==='curso'?'En curso':'Pendiente'}</td><td>${esc(a.nota||'')}</td></tr>`; }).join('')}</table>`;
  const rs=Object.keys(RESP()); if(rs.length) h+=`<h2>Preguntas a la administración y respuestas</h2><table><tr><th>Pregunta</th><th>Respuesta</th></tr>${C.preguntas.filter(x=>RESP()[x.id]&&RESP()[x.id].texto).map(x=>`<tr><td>${esc(x.pregunta)}</td><td>${esc(RESP()[x.id].texto)}</td></tr>`).join('')}</table>`;
  h+=`<h2>Carácter de las decisiones</h2><div>${q.firm?'Se alcanzó el 50 % + 1 del total de propietarios (unidades y porcentual): las decisiones son firmes.':'No se alcanzó el 50 % + 1 del total: las decisiones se consideran proposiciones y se circulan a los ausentes por 15 días (vencimiento '+DEADLINE.toLocaleDateString('es-AR')+'), conforme al art. 2060 del Código Civil y Comercial.'}</div>`;
  const pa=$('#printArea'); pa.innerHTML = pa.innerHTML.replace('<div class="sig">', h+'<div class="sig">'); };

// ---- render hooks
const _renderAll = renderAll;
renderAll = function(){ _renderAll(); if(TAB==='agenda') renderAgenda(); else if(TAB==='preguntas') renderPreguntas(); else if(TAB==='propos') renderPropos(); };
(function(){ let t='agenda'; try{ t=localStorage.getItem(KEY+'-tab')||'agenda'; }catch(e){} setTab(t); })();
"""
s = s.replace("let tt; function toast(msg){", js + "\nlet tt; function toast(msg){")

# renderAll must be reassignable: it is declared with `function renderAll(){...}` → make it `let`? function declarations can be reassigned (they are bindings), OK. buildPrint likewise.
# sync.apply must keep new fields
s = s.replace("const act=Math.min(S.activa, st.mociones.length-1); S={presentes:st.presentes||{}, poderes:st.poderes||{}, mociones:st.mociones, activa:act}; save(); renderAll(); }",
              "const act=Math.min(S.activa, st.mociones.length-1); S={presentes:st.presentes||{}, poderes:st.poderes||{}, mociones:st.mociones, activa:act, agenda:st.agenda||{}, palabra:st.palabra||[], respuestas:st.respuestas||{}, objeciones:st.objeciones||{}}; save(); renderAll(); }")
# fresh state includes new fields
s = s.replace("const fresh = ()=>({ presentes:{}, poderes:{}, activa:0, mociones:[",
              "const fresh = ()=>({ presentes:{}, poderes:{}, activa:0, agenda:{}, palabra:[], respuestas:{}, objeciones:{}, mociones:[")
# 'state' event payload includes new fields already since it sends S
# default mociones: add the two agenda motions
s = s.replace("mociones:[ { titulo:'Que Ramón Gonzalez continúe como encargado', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} } ]",
              "mociones:[ { titulo:'Que Ramón Gonzalez continúe como encargado', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} }, { titulo:'Aprobar el reglamento interno con régimen de multas', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} }, { titulo:'Constituir el tribunal de multas', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} } ]")
# the sticky .top offset: the .top is sticky; with tabs above (46px)
open(p, "w").write(s)
print("patched")
