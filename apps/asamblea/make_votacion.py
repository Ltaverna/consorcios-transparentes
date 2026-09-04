import os
HERE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(HERE, "datos") + "/"
PRIVADO = os.environ.get("CT_PRIVADO", os.path.expanduser("~/consorcio-transparente-privado")) + "/"
import json
SC = HERE + "/"
UNITS = json.load(open(SC + "votacion_units.json"))
from asamblea_content import AGENDA, PREGUNTAS, CONVOCATORIA, PODER
CONTENT = json.dumps(dict(agenda=AGENDA, preguntas=PREGUNTAS, convocatoria=CONVOCATORIA, poder=PODER), ensure_ascii=False).replace("</", "<\\/")
DATA = json.dumps(UNITS, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#1b2536">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Asamblea 2069">
<title>Asamblea Rivadavia 2069</title>
<meta name="description" content="Cómputo de asamblea del Consorcio Rivadavia 2069: presentes, poderes, votos y porcentajes en tiempo real.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600&display=swap">
<style>
:root{
  --bg:#f3f4f6; --surface:#ffffff; --surface-2:#f7f8fa; --ink:#1b2536; --ink-2:#414a58; --muted:#5f6875; --hair:#d5dae2; --hair-2:#e8ebf0;
  --accent:#2a5db0; --accent-soft:#e6eefb;
  --o1:#2a78d6; --o1-soft:#e3eefb; --o2:#eb6834; --o2-soft:#fdeadf; --o3:#8a8f98; --o3-soft:#eceef2; --o4:#1baf7a; --o4-soft:#e0f5ec;
  --good:#0ca30c; --good-soft:#e2f5e2; --warn:#c98500; --warn-soft:#fff3cf; --critical:#d03b3b; --critical-soft:#fbe4e4;
  --good-btn:#0b7d0b; --o1-btn:#1f63bd; --o2-btn:#c44d1c; --o3-btn:#5f6875; --o4-btn:#157d58;
  --tabs-bg:#1b2536; --tabs-ink:#ffffff; --tabs-muted:rgba(255,255,255,.72); --pill-curso-ink:#7a5200; --pill-ok-ink:#0b6a0b; --primary-bg:#1b2536; --primary-ink:#ffffff;
  --shadow:0 1px 2px rgba(27,37,54,.08),0 10px 30px -14px rgba(27,37,54,.25);
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0f1318; --surface:#171c24; --surface-2:#1d232c; --ink:#eef1f5; --ink-2:#c3cad4; --muted:#8e98a6; --hair:#2a313c; --hair-2:#222932;
    --accent:#6f9ee8; --accent-soft:#1c2a42;
    --o1:#3987e5; --o1-soft:#1c2a42; --o2:#d95926; --o2-soft:#3b261a; --o3:#8e98a6; --o3-soft:#262c36; --o4:#199e70; --o4-soft:#16302a;
    --good:#0ca30c; --good-soft:#163016; --warn:#fab219; --warn-soft:#3a3113; --critical:#e66767; --critical-soft:#3a1d1d;
    --good-btn:#0b7d0b; --o1-btn:#1f63bd; --o2-btn:#c44d1c; --o3-btn:#5f6875; --o4-btn:#157d58;
    --tabs-bg:#0b0e13; --tabs-ink:#ffffff; --tabs-muted:rgba(255,255,255,.7); --pill-curso-ink:#ffd27a; --pill-ok-ink:#7fe07f; --primary-bg:#e6eaf0; --primary-ink:#0f1318;
    --shadow:0 1px 2px rgba(0,0,0,.5),0 10px 30px -14px rgba(0,0,0,.7);
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#0f1318; --surface:#171c24; --surface-2:#1d232c; --ink:#eef1f5; --ink-2:#c3cad4; --muted:#8e98a6; --hair:#2a313c; --hair-2:#222932;
  --accent:#6f9ee8; --accent-soft:#1c2a42;
  --o1:#3987e5; --o1-soft:#1c2a42; --o2:#d95926; --o2-soft:#3b261a; --o3:#8e98a6; --o3-soft:#262c36; --o4:#199e70; --o4-soft:#16302a;
  --good:#0ca30c; --good-soft:#163016; --warn:#fab219; --warn-soft:#3a3113; --critical:#e66767; --critical-soft:#3a1d1d;
  --good-btn:#0b7d0b; --o1-btn:#1f63bd; --o2-btn:#c44d1c; --o3-btn:#5f6875; --o4-btn:#157d58;
  --tabs-bg:#0b0e13; --tabs-ink:#ffffff; --tabs-muted:rgba(255,255,255,.7); --pill-curso-ink:#ffd27a; --pill-ok-ink:#7fe07f; --primary-bg:#e6eaf0; --primary-ink:#0f1318;
  --shadow:0 1px 2px rgba(0,0,0,.5),0 10px 30px -14px rgba(0,0,0,.7);
  color-scheme:dark;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
[hidden]{display:none!important}
button,input,select,label{touch-action:manipulation}
input[type=search]{-webkit-appearance:none;appearance:none}
html{-webkit-text-size-adjust:100%;overscroll-behavior-y:contain}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.4;-webkit-font-smoothing:antialiased;padding-bottom:84px}
h1{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:20px;margin:0;letter-spacing:-.01em}
h2{font-size:13px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:0}
button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
input,select{font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--hair);border-radius:8px;padding:8px 10px}
.num{font-variant-numeric:tabular-nums}
.wrap{max-width:900px;margin:0 auto;padding:0 12px}
/* ---- top summary (sticky) */
.top{position:sticky;top:0;z-index:10;background:var(--surface);border-bottom:1px solid var(--hair);box-shadow:var(--shadow)}
.top .wrap{padding:10px 12px 8px;display:grid;gap:8px}
.titlebar{display:flex;align-items:center;justify-content:space-between;gap:10px}
.titlebar .sub{font-size:12px;color:var(--muted)}
.iconbtn{width:40px;height:40px;border-radius:8px;border:1px solid var(--hair);display:inline-flex;align-items:center;justify-content:center;color:var(--ink-2);background:var(--surface);transition:background-color .15s ease,border-color .15s ease}
.iconbtn svg{transition:transform .2s ease}
.top.compact .iconbtn#btnCollapse svg,.iconbtn[aria-expanded="false"] svg{transform:rotate(-90deg)}
.btn svg{vertical-align:-4px;margin-left:2px}
.iconbtn:hover{background:var(--surface-2)}
.mocion{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
.mocion button{white-space:nowrap;padding:6px 12px;border-radius:999px;border:1px solid var(--hair);font-size:13px;font-weight:500;color:var(--ink-2);background:var(--surface)}
.mocion button[aria-pressed="true"]{background:var(--primary-bg);color:var(--primary-ink);border-color:var(--primary-bg)}
.mocion button.add{border-style:dashed;color:var(--muted)}
.quorum{display:grid;grid-template-columns:1fr auto;gap:4px 12px;align-items:baseline}
.quorum .lab{font-size:12px;color:var(--muted);font-weight:500}
.quorum .val{font-size:15px;font-weight:600}
.qbar{grid-column:1/-1;height:6px;border-radius:3px;background:var(--hair-2);overflow:hidden;position:relative}
.qbar i{position:absolute;left:0;top:0;height:100%;background:var(--good);border-radius:3px}
.qbar i.p{background:var(--warn);opacity:.9}
.qbar b{position:absolute;top:-3px;width:2px;height:12px;background:var(--ink);left:50%}
.results{display:grid;gap:10px;padding-top:2px}
.res{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;align-items:baseline}
.res .name{font-weight:600;font-size:14px;display:flex;align-items:center;gap:8px;min-width:0}
.res .name span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.res .name i{width:10px;height:10px;border-radius:3px;flex:none}
.res .pct{font-size:18px;font-weight:700;line-height:1}
.res .meta{grid-column:1/-1;font-size:12px;color:var(--muted);display:flex;gap:4px 0;flex-wrap:wrap;align-items:center}
.res .meta>span:not(.verdict)+span:not(.verdict)::before{content:'·';margin:0 6px;color:var(--hair)}
.res .meta .verdict{margin-left:auto}
.res .bar{grid-column:1/-1;height:8px;border-radius:4px;background:var(--hair-2);overflow:hidden;position:relative}
.res .bar i{display:block;height:100%;border-radius:4px}
.res .bar b{position:absolute;top:-2px;width:2px;height:12px;background:var(--ink);opacity:.6}
.verdict{font-size:11.5px;font-weight:600;padding:3px 8px;border-radius:6px;display:inline-flex;gap:6px;align-items:center;white-space:nowrap}
.verdict.ok{background:var(--good-soft);color:var(--good)} .verdict.no{background:var(--surface-2);color:var(--muted)} .verdict.pend{background:var(--warn-soft);color:var(--warn)}
.top.collapsed .results,.top.collapsed .mocion{display:none}
.mini{display:none;gap:6px 14px;flex-wrap:wrap;font-size:14px;align-items:center}
.mini b{font-weight:700} .mini i{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px;vertical-align:middle}
.mini .q{color:var(--muted);font-weight:500}
.top.compact .mocion,.top.compact .quorum,.top.compact .results,.top.compact .titlebar{display:none}
.top.compact .mini{cursor:pointer;padding-right:26px;position:relative}
.top.compact .mini::after{content:'';position:absolute;right:4px;top:2px;width:14px;height:14px;background:currentColor;-webkit-mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><path d='M6 9l6 6 6-6'/></svg>") center/contain no-repeat;mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><path d='M6 9l6 6 6-6'/></svg>") center/contain no-repeat;color:var(--muted)}
.top.compact .mini{display:flex}
.top.compact .titlebar h1{font-size:15px}
.top.compact .wrap{padding-top:7px;padding-bottom:7px;gap:4px}
.syncdot{width:10px;height:10px;border-radius:50%;background:var(--hair);margin-right:4px}
.syncdot.ok{background:var(--good)} .syncdot.err{background:var(--critical)} .syncdot.busy{background:var(--warn)}
/* ---- toolbar */
.toolbar{display:flex;gap:8px;align-items:center;padding:12px 0 8px;flex-wrap:wrap}
.toolbar input[type=search]{flex:1;min-width:160px}
.toolbar select{font-size:13.5px}
.toolbar .count{font-size:12.5px;color:var(--muted);margin-left:auto}
/* ---- unit rows */
.list{display:grid;gap:6px}
.unit{background:var(--surface);border:1px solid var(--hair);border-radius:10px;padding:10px 12px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px 10px;align-items:center}
.unit.present{border-left:4px solid var(--good)}
.unit.absent{opacity:.75}
.unit .who{min-width:0}
.unit .uf{font-size:12px;color:var(--muted);font-weight:500;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.unit .uf b{color:var(--ink);font-weight:600;font-size:13px}
.unit .prop{font-weight:600;font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.unit .coef{font-size:13px;font-weight:600;color:var(--ink-2);white-space:nowrap}
.unit .acts{grid-column:1/-1;display:grid;gap:6px}
.unit .acts .r1,.unit .acts .r2{display:flex;gap:6px;align-items:stretch}
.unit .acts .r1 .tog{flex:1 1 0}
.unit .acts .r1 .tog.multi{flex:0 0 auto}
.unit .acts .r2 .tog{flex:1 1 0;text-align:center;padding-left:6px;padding-right:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tog{padding:7px 11px;border-radius:8px;border:1px solid var(--hair);font-size:13px;font-weight:600;color:var(--ink-2);background:var(--surface);min-height:36px;transition:background-color .15s ease,border-color .15s ease,color .15s ease;position:relative}
.tog[aria-pressed="true"]::before{content:'';display:inline-block;width:14px;height:14px;margin-right:5px;vertical-align:-2px;background:currentColor;-webkit-mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'><path d='M5 12.5l4.5 4.5L19 7.5'/></svg>") center/contain no-repeat;mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'><path d='M5 12.5l4.5 4.5L19 7.5'/></svg>") center/contain no-repeat}
@media (hover:hover){.tog:not([aria-pressed="true"]):not(:disabled):hover{background:var(--surface-2);border-color:var(--muted)} .btn:hover{background:var(--surface-2)} .chipu:not(.on):not(.poder):hover{border-color:var(--muted)}}
.tog[aria-pressed="true"]{color:#fff;border-color:transparent}
.tog.pres[aria-pressed="true"]{background:var(--good-btn)}
.tog.poder[aria-pressed="true"]{background:#b47600;color:#fff}
.tog.o1[aria-pressed="true"]{background:var(--o1-btn)} .tog.o2[aria-pressed="true"]{background:var(--o2-btn)} .tog.o3[aria-pressed="true"]{background:var(--o3-btn)} .tog.o4[aria-pressed="true"]{background:var(--o4-btn)}
.tog:disabled{opacity:.4;cursor:not-allowed}
.tog.multi{border-style:dashed;color:var(--muted);font-weight:500;font-size:12px}
.sep{width:1px;height:22px;background:var(--hair);margin:0 2px}
.poderinput{grid-column:1/-1;display:flex;gap:6px;align-items:center;font-size:13px;color:var(--ink-2)}
.poderinput input{flex:1;padding:8px 10px;font-size:16px}
/* ---- pasar lista */
.roll{display:grid;gap:14px}
.roll .floor{display:grid;gap:6px}
.roll .floor h2{padding:0 2px}
.roll .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px}
.chipu{display:grid;grid-template-columns:minmax(0,1fr) auto;border:1px solid var(--hair);border-radius:10px;background:var(--surface);overflow:hidden;min-height:52px;transition:background-color .15s ease,border-color .15s ease}
.chipu.on .main b::before{content:'';display:inline-block;width:13px;height:13px;margin-right:5px;vertical-align:-1px;background:#fff;-webkit-mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'><path d='M5 12.5l4.5 4.5L19 7.5'/></svg>") center/contain no-repeat;mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'><path d='M5 12.5l4.5 4.5L19 7.5'/></svg>") center/contain no-repeat}
.chipu .main{text-align:left;padding:7px 10px;min-width:0;display:grid;gap:1px}
.chipu .main b{font-size:14px}
.chipu .main span{font-size:12px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chipu .pd{border-left:1px solid var(--hair);padding:0 9px;font-size:11px;font-weight:700;color:var(--muted);letter-spacing:.04em}
.chipu.on{background:var(--good-btn);border-color:var(--good-btn)}
.chipu.on .main b,.chipu.on .main span{color:#fff}
.chipu.on .pd{color:#fff;border-color:rgba(255,255,255,.35)}
.chipu.poder{background:#b47600;border-color:#b47600}
.chipu.poder .main b,.chipu.poder .main span{color:#fff}
.chipu.poder .pd{color:#fff;border-color:rgba(255,255,255,.35)}
.rollhead{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 0 4px;flex-wrap:wrap}
.rollhead .note{flex:1}

/* ---- pestañas y vistas */
.tabs{position:sticky;top:0;z-index:12;background:var(--tabs-bg);color:var(--tabs-ink);display:flex;align-items:stretch;gap:0;overflow-x:auto;scrollbar-width:none;padding:0 6px}
.tabs button{flex:1 0 auto;min-width:64px;padding:12px 10px 10px;font-size:13px;font-weight:600;color:var(--tabs-muted);border-bottom:3px solid transparent;white-space:nowrap;transition:color .15s ease,border-color .15s ease}
.tabs button[aria-selected="true"]{color:var(--tabs-ink);border-bottom-color:var(--tabs-ink)}
.tabs .brand{flex:0 0 auto;align-self:center;font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:15px;padding:0 10px 0 6px;color:var(--tabs-ink);white-space:nowrap}
.top{top:46px}
.view{display:grid;gap:14px;padding:14px 0 24px}
.view h2.sec{font-family:"Source Serif 4",Georgia,serif;font-size:22px;letter-spacing:-.01em;text-transform:none;color:var(--ink)}
.lead{color:var(--ink-2);font-size:15px;max-width:70ch}
.card{background:var(--surface);border:1px solid var(--hair);border-radius:12px;padding:14px 16px;display:grid;gap:10px}
.card h3{margin:0;font-size:17px;line-height:1.3}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:3px 9px;border-radius:999px;background:var(--surface-2);color:var(--ink-2)}
.pill.curso{background:var(--warn-soft);color:var(--pill-curso-ink)} .pill.tratado{background:var(--good-soft);color:var(--pill-ok-ink)} .pill.pend{background:var(--surface-2)}
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

/* ---- bottom bar */
.bottom{position:fixed;left:0;right:0;bottom:0;z-index:10;background:var(--surface);border-top:1px solid var(--hair);padding:8px 12px calc(8px + env(safe-area-inset-bottom))}
.bottom .wrap{display:flex;gap:8px;justify-content:center;padding:0}
.bottom .btn{flex:1 1 0;white-space:nowrap;padding-left:8px;padding-right:8px}
.btn{padding:9px 14px;border-radius:8px;border:1px solid var(--hair);font-size:13.5px;font-weight:600;background:var(--surface);color:var(--ink-2);transition:background-color .15s ease,border-color .15s ease,opacity .15s ease}
.btn:disabled{opacity:.55;cursor:progress}
.btn.primary{background:var(--primary-bg);color:var(--primary-ink);border-color:var(--primary-bg)}
.btn.danger{color:var(--critical)}
/* ---- dialog */
dialog{border:0;border-radius:12px;padding:0;max-width:min(560px,94vw);width:100%;background:var(--surface);color:var(--ink);box-shadow:var(--shadow);margin:6vh auto auto;max-height:86vh;overflow:auto}
dialog::backdrop{background:rgba(10,14,20,.5)}
dialog .body{padding:18px;display:grid;gap:12px;overflow:hidden}
dialog input,dialog select,dialog textarea{width:100%;min-width:0;max-width:100%;box-sizing:border-box}
dialog label>*{min-width:0}
dialog h3{margin:0;font-size:17px}
dialog label{display:grid;gap:4px;font-size:13px;color:var(--ink-2);font-weight:500}
dialog .row{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}
dialog textarea{font:inherit;font-size:12.5px;width:100%;min-height:220px;border:1px solid var(--hair);border-radius:8px;padding:10px;background:var(--surface-2);color:var(--ink);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.note{font-size:12.5px;color:var(--muted)}
.opts{display:grid;gap:6px}
.opts .opt{display:grid;grid-template-columns:14px minmax(0,1fr) auto;gap:8px;align-items:center}
.opts .opt input{min-width:0}
.opts .opt i{width:12px;height:12px;border-radius:3px}
.toast{position:fixed;left:50%;bottom:80px;transform:translateX(-50%);background:var(--primary-bg);color:var(--primary-ink);padding:8px 14px;border-radius:8px;font-size:13px;display:none;z-index:20}

/* ---- teléfono: todo más grande y claro */
@media (max-width:640px){
  body{font-size:17px}
  h1{font-size:19px}
  .titlebar .sub{font-size:13px}
  .quorum .lab{font-size:14px} .quorum .val{font-size:22px}
  .qbar{height:9px}
  .res .name{font-size:16px} .res .pct{font-size:26px} .res .meta{font-size:13.5px} .res .bar{height:10px}
  .verdict{font-size:12.5px;padding:4px 9px}
  .mocion button{font-size:14px;padding:8px 14px}
  .toolbar input[type=search],.toolbar select{font-size:16px;padding:11px 12px;min-height:46px}
  .unit{padding:12px 12px}
  .unit .uf{font-size:13.5px} .unit .uf b{font-size:15px} .unit .prop{font-size:18px} .unit .coef{font-size:16px}
  .tog{padding:11px 10px;font-size:15.5px;min-height:48px;border-radius:10px}
  .unit .acts .r2 .tog{font-size:15px}
  input,select,textarea{font-size:16px!important}
  .mini{font-size:14.5px}
  .tog.multi{font-size:13px}
  .chipu{min-height:62px} .chipu .main{padding:9px 12px} .chipu .main b{font-size:17px} .chipu .main span{font-size:13.5px} .chipu .pd{font-size:14px;padding:0 13px}
  .roll .grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .roll .floor h2{font-size:14px}
  .rollhead .note{font-size:14px}
  .btn{padding:12px 14px;font-size:15px;min-height:46px}
  .bottom .wrap{gap:6px}
  .titlebar .sub{display:none}
  .results .note{display:none}
  dialog .body{padding:16px}
  dialog input,dialog select{font-size:16px;padding:11px 12px}
  .note{font-size:14px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
#printArea{font-family:"IBM Plex Sans",system-ui,sans-serif;color:#000;background:#fff;padding:20px;max-width:900px;margin:0 auto}
#printArea h1{font-size:20px;margin:0 0 4px} #printArea h2{font-size:14px;letter-spacing:0;text-transform:none;color:#000;margin:18px 0 6px;font-weight:700}
#printArea table{border-collapse:collapse;width:100%;font-size:12px;margin-bottom:8px} #printArea th,#printArea td{border:1px solid #bbb;padding:4px 6px;text-align:left} #printArea th{background:#eee} #printArea td.r,#printArea th.r{text-align:right}
#printArea .sig{margin-top:40px;display:flex;gap:40px} #printArea .sig div{flex:1;border-top:1px solid #000;padding-top:4px;font-size:12px}
@media print{ body{background:#fff;padding:0} .top,.toolbar,.list,.roll,.bottom,.toast,dialog{display:none!important} #printArea{display:block!important} @page{margin:14mm} }
</style>

<nav class="tabs" role="tablist" aria-label="Secciones">
  <span class="brand">Rivadavia 2069</span>
  <button role="tab" data-tab="agenda" aria-selected="true">Agenda</button>
  <button role="tab" data-tab="votar" aria-selected="false">Votar</button>
  <button role="tab" data-tab="preguntas" aria-selected="false">Preguntas</button>
  <button role="tab" data-tab="propos" aria-selected="false">Proposiciones</button>
  <button role="tab" data-tab="docs" aria-selected="false">Documentos</button>
</nav>
<div class="top" id="top">
  <div class="wrap">
    <div class="titlebar">
      <div><h1>Votar</h1><div class="sub" id="subtitle">Asamblea · 116 unidades · porcentual columna A</div></div>
      <div style="display:flex;gap:6px;align-items:center"><span class="syncdot" id="syncdot" title="Sincronización"></span><button class="iconbtn" id="btnCollapse" title="Mostrar/ocultar resultados" aria-label="Mostrar u ocultar resultados" aria-expanded="true"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button><button class="iconbtn" id="btnSettings" title="Configurar moción" aria-label="Configurar moción"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg></button></div>
    </div>
    <div class="mocion" id="mociones"></div>
    <div class="mini" id="mini" title="Tocá para ver el detalle"></div>
    <div class="quorum" id="quorum"></div>
    <div class="results" id="results"></div>
  </div>
</div>

<div class="wrap" id="votarWrap">
  <div class="toolbar">
    <input id="q" type="search" placeholder="Buscar propietario, piso o UF…" aria-label="Buscar">
    <select id="filter" aria-label="Filtrar"><option value="">Todas las unidades</option><option value="present">Presentes y con poder</option><option value="absent">Ausentes</option><option value="unvoted">Presentes sin votar</option><option value="voted">Con voto</option><option value="depto">Departamentos y local</option><option value="cochera">Cocheras</option></select>
    <span class="count" id="count"></span>
  </div>
  <div class="list" id="list"></div>
  <div class="roll" id="roll" hidden></div>
</div>


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

<div class="bottom"><div class="wrap">
  <button class="btn primary" id="btnLista">Pasar lista</button>
  <button class="btn" id="btnResumen">Acta</button>
  <button class="btn" id="btnExport">Exportar</button>
  <button class="btn" id="btnMas" aria-label="Más opciones">Más <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg></button>
</div></div>
<dialog id="dlgMas"><div class="body">
  <h3>Más opciones</h3>
  <div class="opts" style="gap:8px">
    <button class="btn" id="btnPresentes">Marcar presentes por texto…</button>
    <button class="btn" id="btnSettings2">Configurar moción y sincronización</button>
    <button class="btn" id="btnPlanilla">Cargar precarga de la planilla</button>
    <button class="btn danger" id="btnReset">Reiniciar toda la votación</button>
  </div>
  <div class="row"><button class="btn" id="btnMasCerrar">Cerrar</button></div>
</div></dialog>

<dialog id="dlgSettings"><form method="dialog" class="body">
  <h3>Moción</h3>
  <label>Título de la moción <input id="sTitulo" placeholder="Ej.: Que Ramón Gonzalez continúe como encargado"></label>
  <div class="opts" id="sOpts"></div>
  <label>Regla de aprobación
    <select id="sRegla"><option value="abs">Mayoría absoluta: más del 50% del total (unidades y porcentual)</option><option value="pres">Mayoría simple de los presentes (unidades y porcentual)</option><option value="2/3">Dos tercios del total (unidades y porcentual)</option></select>
  </label>
  <p class="note">Doble mayoría según art. 2060 del Código Civil y Comercial: se computa a la vez la cantidad de unidades y el porcentual. Las abstenciones no suman a ninguna opción.</p>
  <h3 style="margin-top:6px">Sincronización con Google Sheets</h3>
  <label>URL de la aplicación web (Apps Script) <input id="sUrl" placeholder="https://script.google.com/macros/s/…/exec" inputmode="url"></label>
  <label>Nombre de este dispositivo <input id="sDev" placeholder="Ej.: celular Hugo"></label>
  <p class="note" id="sStatus" role="status" aria-live="polite">Conectado a la hoja de Google. No hace falta cambiar nada.</p>
  <div class="row"><button class="btn danger" id="sBorrar" type="button">Borrar esta moción</button><button class="btn" value="cancel">Cancelar</button><button class="btn primary" id="sGuardar" value="ok">Guardar</button></div>
</form></dialog>

<dialog id="dlgResumen"><div class="body">
  <h3>Resumen para el acta</h3>
  <textarea id="resumenTxt" readonly></textarea>
  <div class="row"><button class="btn" id="btnCopiar">Copiar</button><button class="btn primary" id="btnCerrarResumen">Cerrar</button></div>
</div></dialog>

<dialog id="dlgExport"><div class="body">
  <h3>Exportar</h3>
  <p class="note">Excel con el estado por unidad y los resultados; PDF a través de la impresión del navegador (en el celular: Imprimir → Guardar como PDF).</p>
  <div class="row" style="justify-content:flex-start"><button class="btn primary" id="btnXlsx">Excel (.xlsx)</button><button class="btn primary" id="btnPdf">PDF / imprimir acta</button><button class="btn" id="btnExportCerrar">Cerrar</button></div>
  <p class="note" id="exportNote" role="status" aria-live="polite"></p>
</div></dialog>
<div id="printArea" hidden></div>
<dialog id="dlgPresentes"><div class="body">
  <h3>Marcar presentes</h3>
  <p class="note">Escribí los pisos o UF separados por coma o espacio (ej.: <b>11-B, 4-A, UC-3, 72</b>). Se marcan como presentes sin cambiar los votos.</p>
  <input id="presInput" placeholder="11-B, 4-A, UC-3…">
  <div class="row"><button class="btn" id="btnPresTodos">Marcar todas presentes</button><button class="btn" id="btnPresNinguno">Limpiar presencia</button><button class="btn" id="btnPresCancel">Cerrar</button><button class="btn primary" id="btnPresOk">Marcar</button></div>
</div></dialog>

<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script id="data" type="application/json">__DATA__</script>
<script id="content" type="application/json">__CONTENT__</script>
<script>
(function(){
const UNITS = JSON.parse(document.getElementById('data').textContent);
const TOTAL_PCT = UNITS.reduce((s,u)=>s+u.pct,0);
const N = UNITS.length;
const $ = s=>document.querySelector(s);
const esc = s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fp = v=>v.toFixed(2).replace('.',',')+'%';
const KEY = 'votacion-rivadavia-2069-v5';
const COLORS = ['o1','o2','o3','o4'];

// ---------- state
const CFG_KEY = KEY+'-cfg';
const DEFAULT_URL = 'https://script.google.com/macros/s/AKfycbz_wM4sUwksIA6V6vPL-yt1f3UL3kNYo3NVgfMd_IBfgcWnfC54MsH224GYvp0A8_w/exec';
let CFG = {url:DEFAULT_URL, dev:''}; try{ CFG = Object.assign(CFG, JSON.parse(localStorage.getItem(CFG_KEY)||'{}')); }catch(e){}
if(!CFG.url) CFG.url = DEFAULT_URL;
if(!CFG.dev){ CFG.dev = 'Teléfono ' + Math.floor(1000 + Math.random()*9000); try{ localStorage.setItem(CFG_KEY, JSON.stringify(CFG)); }catch(e){} }
function saveCfg(){ try{ localStorage.setItem(CFG_KEY, JSON.stringify(CFG)); }catch(e){} }
const fresh = ()=>({ presentes:{}, poderes:{}, activa:0, agenda:{}, palabra:[], respuestas:{}, objeciones:{}, mociones:[ { titulo:'Que Ramón Gonzalez continúe como encargado', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} }, { titulo:'Aprobar el reglamento interno con régimen de multas', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} }, { titulo:'Constituir el tribunal de multas', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} } ] });
let S = fresh();
try { const raw = localStorage.getItem(KEY); if(raw){ const p = JSON.parse(raw); if(p && p.mociones && p.mociones.length) S = p; } } catch(e){}
function save(){ try{ localStorage.setItem(KEY, JSON.stringify(S)); }catch(e){} }
const M = ()=>S.mociones[S.activa];
const isAbst = (m,i)=>/^abst/i.test(m.opciones[i]||'');
const participa = u => !!S.presentes[u.uf] || !!S.poderes[u.uf];

// ---------- compute
function compute(m){
  const opts = m.opciones.map((name,i)=>({name,i,pct:0,n:0,abst:isAbst(m,i)}));
  let presN=0, presPct=0, poderN=0, poderPct=0, votN=0, votPct=0;
  for(const u of UNITS){
    const p = !!S.presentes[u.uf], pd = !!S.poderes[u.uf];
    if(p){presN++; presPct+=u.pct;} else if(pd){poderN++; poderPct+=u.pct;}
    if(!(p||pd)) continue;
    const v = m.votos[u.uf];
    if(v!=null && opts[v]){ opts[v].n++; opts[v].pct+=u.pct; if(!opts[v].abst){votN++; votPct+=u.pct;} }
  }
  const partN = presN+poderN, partPct = presPct+poderPct;
  return {opts,presN,presPct,poderN,poderPct,partN,partPct,votN,votPct};
}
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

// ---------- render top
function renderTop(){
  const m = M(); const c = compute(m);
  $('#mociones').innerHTML = S.mociones.map((x,i)=>`<button aria-pressed="${i===S.activa}" data-i="${i}">${esc(x.titulo)}</button>`).join('') + `<button class="add" data-add="1">+ Nueva moción</button>`;
  $('#quorum').innerHTML = `<span class="lab">Quórum: presentes ${c.presN} + poderes ${c.poderN} = <b>${c.partN} de ${N} unidades</b></span><span class="val num">${fp(c.partPct)}</span>
    <div class="qbar" title="Presentes (verde) y poderes (ámbar); la marca es el 50%"><i style="width:${(c.presPct/TOTAL_PCT*100).toFixed(2)}%"></i><i class="p" style="left:${(c.presPct/TOTAL_PCT*100).toFixed(2)}%;width:${(c.poderPct/TOTAL_PCT*100).toFixed(2)}%"></i><b></b></div>`;
  const baseSel = document.createElement('div');
  $('#results').innerHTML = c.opts.map(o=>{
    const v = verdict(m,c,o);
    const sharePres = c.partPct? o.pct/c.partPct*100 : 0;
    const shareVal = c.votPct? o.pct/c.votPct*100 : 0;
    const w = o.pct/TOTAL_PCT*100;
    let vh='';
    if(v){ const needUF = m.regla==='2/3' ? Math.ceil(v.needN) : Math.floor(v.needN)+1;
      vh = v.ok ? `<span class="verdict ok">✓ Aprobada</span>` : `<span class="verdict ${c.partN?'no':'pend'}">Necesita ${needUF} UF y ${fp(v.needPct)} ${v.base}</span>`; }
    const mark = v ? `<b style="left:${(v.needPct/TOTAL_PCT*100).toFixed(2)}%"></b>` : '';
    return `<div class="res"><div class="name"><i style="background:var(--${COLORS[o.i%4]})"></i><span>${esc(o.name)}</span></div><div class="pct num">${fp(o.pct)}</div>
      <div class="bar"><i style="width:${w.toFixed(2)}%;background:var(--${COLORS[o.i%4]})"></i>${mark}</div>
      <div class="meta"><span class="num">${o.n} UF</span><span class="num">${fp(sharePres)} de presentes</span>${o.abst?'':`<span class="num">${fp(shareVal)} de válidos</span>`}${vh}</div></div>`;
  }).join('') + `<div class="note">Total porcentual del edificio: ${fp(TOTAL_PCT)} (redondeo de la planilla). Presentes sin votar: ${c.partN - c.opts.reduce((s,o)=>s+o.n,0)}.</div>`;
  $('#subtitle').textContent = `${esc(m.titulo)} · ${N} unidades · porcentual columna A`;
  $('#mini').innerHTML = `<span class="q">Quórum <b>${fp(c.partPct)}</b> · ${c.partN} UF</span>` + c.opts.map(o=>`<span><i style="background:var(--${COLORS[o.i%4]})"></i>${esc(o.name)} <b class="num">${fp(o.pct)}</b></span>`).join('');
}

// ---------- render list
function rowHTML(u){
  const m = M(); const p=!!S.presentes[u.uf], pd=!!S.poderes[u.uf], part=p||pd; const v=m.votos[u.uf];
  const same = UNITS.filter(x=>x.prop===u.prop).length;
  return `<div class="unit ${part?'present':'absent'}" data-uf="${u.uf}">
    <div class="who"><div class="uf"><b>${esc(u.piso)}</b><span>UF ${u.uf}</span>${u.tipo==='Cochera'?'<span>cochera</span>':''}${same>1?`<span title="Este propietario tiene ${same} unidades">${same} unidades</span>`:''}</div><div class="prop">${esc(u.prop)}</div></div>
    <div class="coef num">${fp(u.pct)}</div>
    <div class="acts">
      <div class="r1"><button class="tog pres" data-act="pres" aria-pressed="${p}">Presente</button><button class="tog poder" data-act="poder" aria-pressed="${pd}">Poder</button>${same>1?`<button class="tog multi" data-act="multi" title="Aplicar presencia y voto a las ${same} unidades de ${esc(u.prop)}">× ${same}</button>`:''}</div>
      <div class="r2">${m.opciones.map((o,i)=>`<button class="tog ${COLORS[i%4]}" data-act="vote" data-i="${i}" aria-pressed="${v===i}" ${part?'':'disabled'}>${esc(o)}</button>`).join('')}</div>
    </div>
    ${pd?`<div class="poderinput"><label for="poder-${u.uf}">Representado por</label><input id="poder-${u.uf}" data-act="poderName" enterkeyhint="done" autocomplete="off" value="${esc(S.poderes[u.uf]===true?'':S.poderes[u.uf])}" placeholder="nombre del apoderado (opcional)"></div>`:''}
  </div>`;
}
function filtered(){
  const q = $('#q').value.trim().toLowerCase(), f = $('#filter').value; const m=M();
  return UNITS.filter(u=>{
    if(q && !(`${u.prop} ${u.piso} ${u.uf}`.toLowerCase().includes(q))) return false;
    const part = participa(u); const v = m.votos[u.uf];
    if(f==='present') return part; if(f==='absent') return !part; if(f==='unvoted') return part && v==null; if(f==='voted') return part && v!=null;
    if(f==='depto') return u.tipo!=='Cochera'; if(f==='cochera') return u.tipo==='Cochera';
    return true;
  });
}
function renderList(){
  const rows = filtered();
  $('#list').innerHTML = rows.map(rowHTML).join('') || `<div class="note" style="padding:20px;text-align:center">Ninguna unidad coincide.</div>`;
  $('#count').textContent = `${rows.length} de ${N}`;
}
function renderRow(uf){
  const el = document.querySelector(`.unit[data-uf="${uf}"]`); const u = UNITS.find(x=>x.uf===uf);
  if(el && u){ const tmp=document.createElement('div'); tmp.innerHTML=rowHTML(u); el.replaceWith(tmp.firstElementChild); }
}
let mode = 'votar';
function floorKey(u){ if(u.tipo==='Cochera') return 'Cocheras'; if(u.piso==='LOC-') return 'Planta baja'; if(u.piso.startsWith('PB')) return 'Planta baja'; return 'Piso '+u.piso.split('-')[0]; }
function renderRoll(){
  const groups=[]; const idx={};
  for(const u of UNITS){ const k=floorKey(u); if(idx[k]==null){ idx[k]=groups.length; groups.push({k,items:[]}); } groups[idx[k]].items.push(u); }
  const c = compute(M());
  $('#roll').innerHTML = `<div class="rollhead"><span class="note">Tocá para marcar <b>presente</b>; <b>P</b> = viene con poder.<br>Presentes <b>${c.presN}</b> · poderes <b>${c.poderN}</b> · quórum <b>${fp(c.partPct)}</b></span><button class="btn primary" id="btnVolver">Listo, ir a votar</button></div>` +
    groups.map(g=>`<div class="floor"><h2>${g.k}</h2><div class="grid">${g.items.map(u=>{ const p=!!S.presentes[u.uf], pd=!!S.poderes[u.uf];
      return `<div class="chipu ${p?'on':pd?'poder':''}" data-uf="${u.uf}"><button class="main" data-act="rpres"><b>${esc(u.piso)}</b><span>${esc(u.prop)}</span></button><button class="pd" data-act="rpoder" title="Con poder">P</button></div>`; }).join('')}</div></div>`).join('');
  $('#btnVolver').addEventListener('click', ()=>setMode('votar'));
}
function setMode(m){ mode=m; pinned=false; const roll = m==='lista'; $('#roll').hidden=!roll; $('#list').hidden=roll; $('.toolbar').hidden=roll; $('#btnLista').textContent = roll?'Volver a votar':'Pasar lista'; renderAll(); window.scrollTo(0,0); applyCompact(); }
$('#roll').addEventListener('click', e=>{ const b=e.target.closest('button[data-act]'); if(!b) return; const uf=+b.closest('.chipu').dataset.uf; const u=UNITS.find(x=>x.uf===uf);
  if(b.dataset.act==='rpres') setPresent(u, !S.presentes[uf]); else setPoder(u, !S.poderes[uf]);
  save(); renderTop(); renderRoll(); });
$('#btnLista').addEventListener('click', ()=>setMode(mode==='lista'?'votar':'lista'));
function renderAll(){ renderTop(); if(mode==='lista') renderRoll(); else renderList(); }

// ---------- actions
function setPresent(u, val){ if(val){ S.presentes[u.uf]=true; delete S.poderes[u.uf]; } else { delete S.presentes[u.uf]; if(!S.poderes[u.uf]) for(const m of S.mociones) delete m.votos[u.uf]; } sync.send({t:'presente', uf:u.uf, v:!!val}); }
function setPoder(u, val){ if(val){ S.poderes[u.uf]=S.poderes[u.uf]||true; delete S.presentes[u.uf]; } else { delete S.poderes[u.uf]; if(!S.presentes[u.uf]) for(const m of S.mociones) delete m.votos[u.uf]; } sync.send({t:'poder', uf:u.uf, v:val?S.poderes[u.uf]:false}); }
function setVote(u, i){ const m=M(); if(m.votos[u.uf]===i) delete m.votos[u.uf]; else m.votos[u.uf]=i; sync.send({t:'voto', m:S.activa, uf:u.uf, v:(m.votos[u.uf]==null?null:m.votos[u.uf])}); }

$('#list').addEventListener('click', e=>{
  const b = e.target.closest('button[data-act]'); if(!b) return;
  const row = b.closest('.unit'); const u = UNITS.find(x=>x.uf===+row.dataset.uf); const act=b.dataset.act;
  if(act==='pres') setPresent(u, b.getAttribute('aria-pressed')!=='true');
  else if(act==='poder') setPoder(u, b.getAttribute('aria-pressed')!=='true');
  else if(act==='vote') setVote(u, +b.dataset.i);
  else if(act==='multi'){
    const sibs = UNITS.filter(x=>x.prop===u.prop && x.uf!==u.uf); const m=M();
    for(const x of sibs){ if(S.presentes[u.uf]){S.presentes[x.uf]=true; delete S.poderes[x.uf];} else if(S.poderes[u.uf]){S.poderes[x.uf]=S.poderes[u.uf]; delete S.presentes[x.uf];} else {delete S.presentes[x.uf]; delete S.poderes[x.uf];}
      if(m.votos[u.uf]!=null) m.votos[x.uf]=m.votos[u.uf]; else delete m.votos[x.uf];
      sync.send({t:'presente', uf:x.uf, v:!!S.presentes[x.uf]}); if(S.poderes[x.uf]) sync.send({t:'poder', uf:x.uf, v:S.poderes[x.uf]}); sync.send({t:'voto', m:S.activa, uf:x.uf, v:(m.votos[x.uf]==null?null:m.votos[x.uf])}); }
    save(); renderAll(); toast(`Aplicado a las ${sibs.length+1} unidades de ${u.prop}`); return;
  }
  save(); renderTop(); renderRow(u.uf);
});
$('#list').addEventListener('change', e=>{ const inp=e.target.closest('input[data-act="poderName"]'); if(!inp) return; const uf=+inp.closest('.unit').dataset.uf; S.poderes[uf]=inp.value.trim()||true; save(); sync.send({t:'poder', uf, v:S.poderes[uf]}); });
$('#q').addEventListener('input', renderList); $('#filter').addEventListener('change', renderList);
let pinned=false;
function applyCompact(){ const top=$('#top'); const c = mode==='lista' ? !pinned : (!pinned && window.scrollY>140); top.classList.toggle('compact', c); $('#btnCollapse').setAttribute('aria-expanded', String(!c)); }
$('#btnCollapse').addEventListener('click', ()=>{ pinned=!pinned; if(pinned) window.scrollTo({top:0}); applyCompact(); });
$('#mini').addEventListener('click', ()=>{ pinned=true; window.scrollTo({top:0}); applyCompact(); });
addEventListener('scroll', ()=>{ if(window.scrollY<=140) pinned=false; applyCompact(); }, {passive:true});
$('#mociones').addEventListener('click', e=>{ const b=e.target.closest('button'); if(!b) return;
  if(b.dataset.add){ S.mociones.push({titulo:`Moción ${S.mociones.length+1}`, opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{}}); S.activa=S.mociones.length-1; save(); sync.send({t:'mociones', v:S.mociones}); renderAll(); openSettings(); return; }
  S.activa=+b.dataset.i; save(); renderAll(); });

// ---------- settings
function openSettings(){ const m=M(); $('#sTitulo').value=m.titulo; $('#sRegla').value=m.regla; $('#sUrl').value=CFG.url; $('#sDev').value=CFG.dev; $('#sStatus').textContent = CFG.url ? ('Conectado a la hoja de Google (estado: '+sync.status+'). Todos los teléfonos comparten la misma votación.') : 'Sin sincronizar: los datos quedan solo en este dispositivo.';
  $('#sOpts').innerHTML = [0,1,2,3].map(i=>`<div class="opt"><i style="background:var(--${COLORS[i]})"></i><input data-opt="${i}" value="${esc(m.opciones[i]||'')}" placeholder="${i<2?'Opción '+(i+1):'(vacío = sin opción)'}"><span class="note">${i>=2?'opcional':''}</span></div>`).join('');
  $('#dlgSettings').showModal(); }
$('#btnSettings').addEventListener('click', openSettings);
$('#sGuardar').addEventListener('click', e=>{ const m=M(); m.titulo=$('#sTitulo').value.trim()||m.titulo; m.regla=$('#sRegla').value;
  const opts=[...document.querySelectorAll('#sOpts input')].map(i=>i.value.trim()); const newOpts=[]; const map={};
  opts.forEach((o,i)=>{ if(o){ map[i]=newOpts.length; newOpts.push(o);} });
  if(newOpts.length<2){ alert('Se necesitan al menos dos opciones.'); e.preventDefault(); return; }
  const nv={}; for(const k in m.votos){ if(map[m.votos[k]]!=null) nv[k]=map[m.votos[k]]; } m.votos=nv; m.opciones=newOpts;
  CFG.url=$('#sUrl').value.trim(); CFG.dev=$('#sDev').value.trim(); saveCfg(); save(); sync.send({t:'mociones', v:S.mociones}); renderAll(); sync.start(); });
$('#sBorrar').addEventListener('click', ()=>{ if(S.mociones.length<=1){ alert('Tiene que quedar al menos una moción.'); return; } if(!confirm('¿Borrar esta moción y sus votos?')) return; S.mociones.splice(S.activa,1); S.activa=0; save(); sync.send({t:'mociones', v:S.mociones}); renderAll(); $('#dlgSettings').close(); });

// ---------- resumen
function resumen(){
  const lines=[]; const d=new Date();
  lines.push(`ASAMBLEA CONSORCIO RIVADAVIA 2069 - ${d.toLocaleDateString('es-AR')} ${d.toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'})}`);
  const c0=compute(S.mociones[0]);
  lines.push(`Quórum: ${c0.presN} unidades presentes (${fp(c0.presPct)}) + ${c0.poderN} por poder (${fp(c0.poderPct)}) = ${c0.partN} de ${N} unidades, ${fp(c0.partPct)} del porcentual (total ${fp(TOTAL_PCT)}).`);
  const pres=UNITS.filter(u=>S.presentes[u.uf]).map(u=>`${u.piso} ${u.prop}`); const pod=UNITS.filter(u=>S.poderes[u.uf]).map(u=>`${u.piso} ${u.prop}${typeof S.poderes[u.uf]==='string'?' (rep. '+S.poderes[u.uf]+')':''}`);
  lines.push(''); lines.push(`Presentes (${pres.length}): ${pres.join('; ')||'-'}`); lines.push(`Por poder (${pod.length}): ${pod.join('; ')||'-'}`);
  S.mociones.forEach((m,k)=>{ const c=compute(m); lines.push(''); lines.push(`MOCIÓN ${k+1}: ${m.titulo}  [regla: ${ {abs:'mayoría absoluta del total',pres:'mayoría simple de presentes','2/3':'dos tercios del total'}[m.regla] }]`);
    c.opts.forEach(o=>{ const v=verdict(m,c,o); lines.push(`  ${o.name}: ${o.n} unidades, ${fp(o.pct)} del porcentual, ${fp(c.partPct?o.pct/c.partPct*100:0)} de los presentes${v?(v.ok?'  -> APROBADA':'  -> no alcanza'):''}`); });
    const sinv = UNITS.filter(u=>participa(u)&&m.votos[u.uf]==null); lines.push(`  Sin votar: ${sinv.length}`);
    c.opts.forEach(o=>{ const who=UNITS.filter(u=>m.votos[u.uf]===o.i).map(u=>u.piso); if(who.length) lines.push(`  ${o.name} - unidades: ${who.join(', ')}`); });
  });
  return lines.join('\n');
}
$('#btnResumen').addEventListener('click', ()=>{ $('#resumenTxt').value=resumen(); $('#dlgResumen').showModal(); });
$('#btnCerrarResumen').addEventListener('click', ()=>$('#dlgResumen').close());
$('#btnCopiar').addEventListener('click', async ()=>{ try{ await navigator.clipboard.writeText($('#resumenTxt').value); toast('Copiado'); }catch(e){ $('#resumenTxt').select(); document.execCommand('copy'); toast('Copiado'); } });

// ---------- presentes masivo
$('#btnMas').addEventListener('click', ()=>$('#dlgMas').showModal()); $('#btnMasCerrar').addEventListener('click', ()=>$('#dlgMas').close());
$('#btnSettings2').addEventListener('click', ()=>{ $('#dlgMas').close(); openSettings(); });
$('#btnPresentes').addEventListener('click', ()=>{ $('#dlgMas').close(); $('#presInput').value=''; $('#dlgPresentes').showModal(); });
$('#btnPresCancel').addEventListener('click', ()=>$('#dlgPresentes').close());
$('#btnPresOk').addEventListener('click', ()=>{ const toks=$('#presInput').value.toUpperCase().split(/[\s,;]+/).filter(Boolean); let n=0;
  for(const t of toks){ const u=UNITS.find(x=>String(x.uf)===t || x.piso.toUpperCase()===t || x.piso.toUpperCase().replace('-','')===t.replace('-','')); if(u){ setPresent(u,true); n++; } }
  save(); renderAll(); $('#dlgPresentes').close(); toast(`${n} unidades marcadas presentes`); });
$('#btnPresTodos').addEventListener('click', ()=>{ for(const u of UNITS) setPresent(u,true); save(); renderAll(); $('#dlgPresentes').close(); });
$('#btnPresNinguno').addEventListener('click', ()=>{ if(!confirm('¿Quitar la presencia de todas las unidades? Los votos también se borran.')) return; S.presentes={}; S.poderes={}; for(const m of S.mociones) m.votos={}; save(); sync.send({t:'state', v:S}); renderAll(); $('#dlgPresentes').close(); });

// ---------- planilla
$('#btnPlanilla').addEventListener('click', ()=>{ $('#dlgMas').close(); if(!confirm('Carga en la moción activa la precarga de la planilla: columna VOTO RAMON como "Continuidad de Ramón" (opción 1) y columna VOTO MIGUEL como "Discontinuar" (opción 2), y marca presentes a esas unidades. ¿Continuar?')) return;
  const m=M(); for(const u of UNITS){ if(u.pre){ if(u.poder){ S.poderes[u.uf]=S.poderes[u.uf]||true; delete S.presentes[u.uf]; } else { S.presentes[u.uf]=true; delete S.poderes[u.uf]; } m.votos[u.uf]=u.pre-1; } }
  save(); sync.send({t:'state', v:S}); renderAll(); toast('Votos de la planilla cargados'); });
$('#btnReset').addEventListener('click', ()=>{ $('#dlgMas').close(); if(!confirm('¿Reiniciar toda la votación? Se borran presentes, poderes y votos de todas las mociones.')) return; S=fresh(); save(); sync.send({t:'reset'}); renderAll(); });

// ---------- sincronización con Google Sheets (Apps Script)
const sync = {
  status:'inactiva', timer:null, queue:[], sending:false, lastServer:0,
  dot(c){ $('#syncdot').className='syncdot '+(c||''); $('#syncdot').title='Sincronización: '+sync.status; },
  start(){ clearInterval(sync.timer); if(!CFG.url){ sync.status='inactiva'; sync.dot(''); return; } sync.status='conectando'; sync.dot('busy');
    sync.send({t:'init', units:UNITS.map(u=>[u.uf,u.piso,u.prop,u.tipo,u.pct])}); sync.pull(); sync.timer=setInterval(sync.pull, 4000); },
  send(ev){ if(!CFG.url) return; ev.ts=Date.now(); ev.dev=CFG.dev||'sin nombre'; sync.queue.push(ev); sync.flush(); },
  async flush(){ if(sync.sending||!sync.queue.length||!CFG.url) return; sync.sending=true; const batch=sync.queue.splice(0, sync.queue.length); sync.dot('busy');
    try{ const r=await fetch(CFG.url,{method:'POST',body:JSON.stringify({events:batch}),redirect:'follow'}); const j=await r.json(); if(j&&j.state) sync.apply(j.state); sync.status='ok'; sync.dot('ok'); }
    catch(e){ sync.queue.unshift(...batch); if(sync.status!=='error: '+e.message) toast('Sin conexión con la hoja: se reintenta solo'); sync.status='error: '+e.message; sync.dot('err'); }
    sync.sending=false; if(sync.queue.length) setTimeout(sync.flush, 1500); },
  async pull(){ if(!CFG.url||sync.sending||sync.queue.length) return; try{ const r=await fetch(CFG.url+(CFG.url.includes('?')?'&':'?')+'t='+Date.now(),{redirect:'follow'}); const j=await r.json(); if(j&&j.state) sync.apply(j.state); sync.status='ok'; sync.dot('ok'); }catch(e){ sync.status='error: '+e.message; sync.dot('err'); } },
  apply(st){ if(!st||!st.mociones||!st.mociones.length) return; if((st.ts||0)<=sync.lastServer) return; sync.lastServer=st.ts||0;
    const act=Math.min(S.activa, st.mociones.length-1); S={presentes:st.presentes||{}, poderes:st.poderes||{}, mociones:st.mociones, activa:act, agenda:st.agenda||S.agenda||{}, palabra:st.palabra||S.palabra||[], respuestas:st.respuestas||S.respuestas||{}, objeciones:st.objeciones||S.objeciones||{}}; if(st.agenda===undefined) sync.legacy=true; save(); renderAll(); }
};
sync.start();
// ---------- exportar
function exportRows(){
  const mocs=S.mociones;
  const head=['UF','Piso-Depto','Propietario','Tipo','Porcentual (%)','Presente','Poder'].concat(mocs.map(m=>m.titulo));
  const rows=UNITS.map(u=>{ const p=!!S.presentes[u.uf], pd=S.poderes[u.uf]; return [u.uf,u.piso,u.prop,u.tipo,u.pct,p?'SI':'',pd?(typeof pd==='string'?pd:'SI'):''].concat(mocs.map(m=>m.votos[u.uf]==null?'':(m.opciones[m.votos[u.uf]]||''))); });
  return {head,rows};
}
function exportSummary(){
  const out=[]; const c0=compute(S.mociones[0]);
  out.push(['Asamblea Consorcio Rivadavia 2069', new Date().toLocaleString('es-AR')]);
  out.push(['Total porcentual del edificio', TOTAL_PCT]); out.push(['Unidades presentes', c0.presN, c0.presPct]); out.push(['Unidades por poder', c0.poderN, c0.poderPct]); out.push(['Quórum (unidades / porcentual)', c0.partN, c0.partPct]); out.push([]);
  S.mociones.forEach(m=>{ const c=compute(m); out.push(['MOCIÓN: '+m.titulo,'Unidades','Porcentual (%)','% de presentes','% de válidos','Resultado']);
    c.opts.forEach(o=>{ const v=verdict(m,c,o); out.push([o.name,o.n,+o.pct.toFixed(2),+(c.partPct?o.pct/c.partPct*100:0).toFixed(2),o.abst?'':+(c.votPct?o.pct/c.votPct*100:0).toFixed(2),v?(v.ok?'APROBADA':'no alcanza'):'']); });
    out.push(['Regla', {abs:'mayoría absoluta del total',pres:'mayoría simple de presentes','2/3':'dos tercios del total'}[m.regla]]); out.push([]); });
  return out;
}
function loadScript(src){ return new Promise((res,rej)=>{ if(document.querySelector(`script[src="${src}"]`)) return res(); const sc=document.createElement('script'); sc.src=src; sc.onload=res; sc.onerror=()=>rej(new Error('No se pudo cargar la librería')); document.head.appendChild(sc); }); }
async function exportXlsx(){
  const b=$('#btnXlsx'); b.disabled=true; const lbl=b.textContent; b.textContent='Generando…'; $('#exportNote').textContent='Preparando el archivo…';
  try{ await loadScript('https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js');
    const wb=XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(exportSummary()), 'Resultados');
    S.mociones.forEach((m,k)=>{ const c=compute(m); const rows=[['MOCIÓN '+(k+1)+': '+m.titulo],['Regla',{abs:'mayoría absoluta del total',pres:'mayoría simple de presentes','2/3':'dos tercios del total'}[m.regla]],['Quórum (unidades / porcentual)',c.partN,+c.partPct.toFixed(2)],[],['Opción','Unidades','Porcentual (%)','% de presentes','% de válidos','Resultado']];
      c.opts.forEach(o=>{ const v=verdict(m,c,o); rows.push([o.name,o.n,+o.pct.toFixed(2),+(c.partPct?o.pct/c.partPct*100:0).toFixed(2),o.abst?'':+(c.votPct?o.pct/c.votPct*100:0).toFixed(2),v?(v.ok?'APROBADA':'no alcanza'):'']); });
      rows.push(['Presentes sin votar', UNITS.filter(u=>participa(u)&&m.votos[u.uf]==null).length]); rows.push([]);
      rows.push(['UF','Piso-Depto','Propietario','Porcentual (%)','Presente / poder','Voto']);
      UNITS.forEach(u=>{ const pd=S.poderes[u.uf]; rows.push([u.uf,u.piso,u.prop,u.pct,S.presentes[u.uf]?'Presente':(pd?('Poder'+(typeof pd==='string'?' ('+pd+')':'')):''), m.votos[u.uf]==null?'':(m.opciones[m.votos[u.uf]]||'')]); });
      const ws=XLSX.utils.aoa_to_sheet(rows); ws['!cols']=[{wch:6},{wch:10},{wch:32},{wch:14},{wch:18},{wch:14}];
      XLSX.utils.book_append_sheet(wb, ws, ('Moción '+(k+1)+' - '+m.titulo).replace(/[\[\]\*\/\\?:]/g,' ').slice(0,31)); });
    const er=exportRows(); const wu=XLSX.utils.aoa_to_sheet([er.head].concat(er.rows)); wu['!cols']=[{wch:6},{wch:10},{wch:32},{wch:13},{wch:14},{wch:9},{wch:12}]; XLSX.utils.book_append_sheet(wb, wu, 'Unidades');
    const d=new Date(); const name=`Votacion Rivadavia 2069 ${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}${String(d.getMinutes()).padStart(2,'0')}.xlsx`;
    XLSX.writeFile(wb, name); $('#exportNote').textContent='Descargado: '+name; }
  catch(e){ $('#exportNote').textContent='No se pudo exportar: '+e.message+'. Si estás viendo la app dentro de claude.ai, abrila desde asamblea.neuralcore.dev para descargar.'; }
  b.disabled=false; b.textContent=lbl;
}
function buildPrint(){
  const d=new Date(); const c0=compute(S.mociones[0]);
  let h=`<h1>Asamblea · Consorcio de Propietarios Rivadavia 2069</h1><div>${d.toLocaleDateString('es-AR')} ${d.toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'})}</div>`;
  h+=`<h2>Quórum</h2><table><tr><th></th><th class="r">Unidades</th><th class="r">Porcentual</th></tr><tr><td>Presentes</td><td class="r">${c0.presN}</td><td class="r">${fp(c0.presPct)}</td></tr><tr><td>Por poder</td><td class="r">${c0.poderN}</td><td class="r">${fp(c0.poderPct)}</td></tr><tr><th>Total</th><th class="r">${c0.partN} de ${N}</th><th class="r">${fp(c0.partPct)} de ${fp(TOTAL_PCT)}</th></tr></table>`;
  S.mociones.forEach((m,k)=>{ const c=compute(m); h+=`<h2>Moción ${k+1}: ${esc(m.titulo)}</h2><table><tr><th>Opción</th><th class="r">Unidades</th><th class="r">Porcentual</th><th class="r">% presentes</th><th class="r">% válidos</th><th>Resultado</th></tr>`;
    c.opts.forEach(o=>{ const v=verdict(m,c,o); h+=`<tr><td>${esc(o.name)}</td><td class="r">${o.n}</td><td class="r">${fp(o.pct)}</td><td class="r">${fp(c.partPct?o.pct/c.partPct*100:0)}</td><td class="r">${o.abst?'—':fp(c.votPct?o.pct/c.votPct*100:0)}</td><td>${v?(v.ok?'APROBADA':'No alcanza'):''}</td></tr>`; });
    h+=`</table><div style="font-size:11px">Regla: ${ {abs:'mayoría absoluta del total (unidades y porcentual)',pres:'mayoría simple de los presentes (unidades y porcentual)','2/3':'dos tercios del total (unidades y porcentual)'}[m.regla] }</div>`; });
  const er=exportRows();
  h+=`<h2>Detalle por unidad</h2><table><tr>${er.head.map((x,i)=>`<th class="${i===4?'r':''}">${esc(x)}</th>`).join('')}</tr>${er.rows.filter(r=>r[5]||r[6]).map(r=>`<tr>${r.map((x,i)=>`<td class="${i===4?'r':''}">${i===4?fp(x):esc(x)}</td>`).join('')}</tr>`).join('')}</table>`;
  h+=`<div class="sig"><div>Presidente de la asamblea</div><div>Secretario</div><div>Propietario</div></div>`;
  $('#printArea').innerHTML=h;
}
$('#btnExport').addEventListener('click', ()=>{ $('#exportNote').textContent=''; $('#dlgExport').showModal(); });
$('#btnExportCerrar').addEventListener('click', ()=>$('#dlgExport').close());
$('#btnXlsx').addEventListener('click', exportXlsx);
$('#btnPdf').addEventListener('click', ()=>{ buildPrint(); $('#dlgExport').close(); $('#printArea').hidden=false; setTimeout(()=>{ window.print(); setTimeout(()=>{ $('#printArea').hidden=true; }, 500); }, 50); });

// ================= asamblea: pestañas, moderador, agenda, preguntas, proposiciones
const C = JSON.parse(document.getElementById('content').textContent);
const fmt = new Intl.NumberFormat('es-AR',{style:'currency',currency:'ARS',maximumFractionDigits:0});
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
  $('#modbar').innerHTML = (sync.legacy?`<span style="color:var(--critical)"><b>La hoja de Google tiene el script anterior:</b> agenda, oradores, respuestas y objeciones no se están guardando. Pegá el Code.gs nuevo y creá una nueva versión.</span><br>`:'') + (MOD ? `<span><b>Modo moderador</b> activo en este dispositivo</span><button class="btn sm" id="btnModOff">Salir</button>` : `<span>Ves la asamblea en vivo. Para marcar presencia, votos y agenda:</span><button class="btn primary sm" id="btnModOn">Soy moderador</button>`);
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

let tt; function toast(msg){ const t=$('#toast'); t.textContent=msg; t.style.display='block'; clearTimeout(tt); tt=setTimeout(()=>t.style.display='none',1800); }
renderAll();
})();
</script>
"""
out = HTML.replace("__DATA__", DATA).replace("__CONTENT__", CONTENT)
open(SC + "votacion-rivadavia-2069.html", "w", encoding="utf-8").write(out)
open(SC + "pages-out/index.html", "w", encoding="utf-8").write("<!doctype html>\n<html lang=\"es\">\n" + out + "\n</html>\n")
print("ok")
