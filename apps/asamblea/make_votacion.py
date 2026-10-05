import os
HERE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(HERE, "datos") + "/"
PRIVADO = os.environ.get("CT_PRIVADO", os.path.expanduser("~/consorcio-transparente-privado")) + "/"
import json
SC = HERE + "/"
LOGICA = open(SC + "logica.js", encoding="utf-8").read()
MARKED = open(SC + "vendor/marked.min.js", encoding="utf-8").read()
UNITS = json.load(open(SC + "votacion_units.json"))
from asamblea_content import AGENDA, PREGUNTAS, CONVOCATORIA, PODER
from normativa import NORMATIVA
REGLAMENTO = open(SC + "reglamento.md", encoding="utf-8").read()
ENCARGADO = open(SC + "encargado.md", encoding="utf-8").read()
INFORME_ADMIN = open(SC + "informe_admin.md", encoding="utf-8").read()
CONTENT = json.dumps(dict(agenda=AGENDA, preguntas=PREGUNTAS, convocatoria=CONVOCATORIA, poder=PODER, reglamento=REGLAMENTO, normativa=NORMATIVA, encargado=ENCARGADO, informe_admin=INFORME_ADMIN), ensure_ascii=False).replace("</", "<\\/")
DATA = json.dumps(UNITS, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#1b2536">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Asamblea 2069">
<title>Asamblea Rivadavia 2069</title>
<meta name="description" content="Cómputo de asamblea del Consorcio Rivadavia 2069: presentes, poderes, votos y porcentajes en tiempo real.">
<!-- ui-ux-pro-max tokens v2: Accessible & Ethical / Government-Institutional
     Estilo: minimalismo institucional — "documento oficial moderno y confiable"
     Paleta luz: bg #f4f6f9 · surface #ffffff · navy #0f172a · accent #1e50a2 · good #0a6b3e · warn #92540a · critical #b91c1c
     Paleta oscuro: bg #0a0e15 · surface #111827 · surface-2 #1a2233
     Tipo: Inter 400/500/600/700 (body, UI, tabular-nums) + Source Serif 4 opsz 600 (títulos, marca, números clave)
     Escala tipo: 11 / 12 / 13 / 14 / 15 / 17 / 20 / 22 / 28px
     Espaciado: base 4px; escala 4/8/12/16/24/32/48
     Radios: input 6px, card 12px, pill 999px — conservador, institucional
     Sombras: capa 1 tint sutil + capa 2 difusa; oscuro más opacas
     Modo oscuro: tonos desaturados con tinte azul-gris; contraste AA garantizado en ambos modos
     Cumplimiento: colapsable en móvil (<640px) via clase .cump-collapsed -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700&display=swap">
<!-- fallback: si Google Fonts no carga, Inter → system-ui (sans), Source Serif 4 → Georgia (serif) -->
<style>
/* ================================================================
   Design tokens — ui-ux-pro-max v2 · Accessible & Ethical · Government-Institutional
   Estilo: minimalismo institucional ("documento oficial moderno y confiable")
   Paleta Government/Public Service · Inter + Source Serif 4
   ================================================================ */
:root{
  /* ── Superficies ──────────────────────────────────────────────── */
  --bg:#f4f6f9;        /* fondo general: gris cálido muy suave */
  --surface:#ffffff;   /* tarjetas y paneles */
  --surface-2:#f0f3f7; /* superficies secundarias, rows alternas */
  --ink:#0f172a;       /* texto principal — navy profundo (contraste 16:1 s/blanco) */
  --ink-2:#334155;     /* texto secundario (7:1 s/blanco) */
  --muted:#64748b;     /* metadatos, labels (4.6:1 s/blanco) */
  --hair:#dde2ea;      /* bordes sutiles */
  --hair-2:#eaecf2;    /* separadores internos */

  /* ── Acento institucional ─────────────────────────────────────── */
  --accent:#1e50a2;        /* azul institucional — solo para links y foco */
  --accent-soft:#e6edf8;   /* fondo tenue de acento */
  --accent-ink:#163d80;    /* texto de acento sobre soft (6.5:1) */

  /* ── Opciones de votación ─────────────────────────────────────── */
  --o1:#1a5fb4; --o1-soft:#deeafa;
  --o2:#b94c00; --o2-soft:#fde8d8;   /* naranja más oscuro → mejor contraste */
  --o3:#4b5563; --o3-soft:#e9ebee;
  --o4:#0a6b3e; --o4-soft:#d4f0e3;

  /* ── Estados semánticos WCAG AA sobre soft ────────────────────── */
  /* Presente/aprobado — verde (#0a6b3e: 5.1:1 s/#d4f0e3) */
  --good:#0a6b3e; --good-soft:#d4f0e3; --good-ink:#084f2e;
  /* Poder/advertencia — ámbar (#92540a: 4.6:1 s/#fdf0d0) */
  --warn:#92540a; --warn-soft:#fdf0d0; --warn-ink:#7a4200;
  /* Alerta/tope superado — rojo (#b91c1c: 5.5:1 s/#fde8e8) */
  --critical:#b91c1c; --critical-soft:#fde8e8; --critical-ink:#991515;

  /* ── Botones de estado activo ─────────────────────────────────── */
  --good-btn:#09603a; --o1-btn:#1a5fb4; --o2-btn:#b94c00; --o3-btn:#3d4754; --o4-btn:#09603a;

  /* ── Barra de pestañas ────────────────────────────────────────── */
  --tabs-bg:#0f172a;              /* navy institucional */
  --tabs-ink:#f8fafc;
  --tabs-muted:rgba(248,250,252,.55);
  --tabs-active-line:#e8b84b;     /* línea dorada — acento único, con mesura */
  --tabs-active-bg:rgba(232,184,75,.10); /* leve wash dorado en tab activa */

  /* ── Pills ────────────────────────────────────────────────────── */
  --pill-curso-ink:#7a4200; --pill-ok-ink:#084f2e;

  /* ── Botón primario ───────────────────────────────────────────── */
  --primary-bg:#0f172a; --primary-ink:#f8fafc;

  /* ── Sombras: capa 1 tint + capa 2 difusa (4dp / 1dp) ─────────── */
  --shadow:0 1px 3px rgba(15,23,42,.08),0 6px 20px -8px rgba(15,23,42,.16);
  --shadow-sm:0 1px 2px rgba(15,23,42,.06),0 3px 10px -5px rgba(15,23,42,.10);
  --shadow-top:0 -1px 3px rgba(15,23,42,.06),0 -4px 12px -6px rgba(15,23,42,.10);

  /* ── Radios — conservador/institucional ──────────────────────── */
  --r-sm:6px;   /* inputs, togs */
  --r-md:12px;  /* tarjetas */
  --r-lg:16px;  /* dialogs */

  color-scheme:light;
}

/* ── Modo oscuro automático ───────────────────────────────────── */
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#080c12; --surface:#111827; --surface-2:#1a2233; --ink:#e8ecf2; --ink-2:#aab4c4; --muted:#7c8ea3; --hair:#1e2a3a; --hair-2:#162030;
    --accent:#5b8fdb; --accent-soft:#16233a; --accent-ink:#8db5f0;
    --o1:#4a8fea; --o1-soft:#132238; --o2:#e06020; --o2-soft:#32190a; --o3:#7c8ea3; --o3-soft:#1e2a3a; --o4:#1db368; --o4-soft:#0a2518;
    --good:#1db368; --good-soft:#0a2518; --good-ink:#60d9a0;
    --warn:#e8a020; --warn-soft:#30200a; --warn-ink:#f2c060;
    --critical:#e85555; --critical-soft:#300f0f; --critical-ink:#f09090;
    --good-btn:#178a52; --o1-btn:#3070d0; --o2-btn:#c84c10; --o3-btn:#3d4754; --o4-btn:#178a52;
    --tabs-bg:#05080e; --tabs-ink:#f8fafc; --tabs-muted:rgba(248,250,252,.5); --tabs-active-line:#e8b84b; --tabs-active-bg:rgba(232,184,75,.08);
    --pill-curso-ink:#f2c060; --pill-ok-ink:#60d9a0;
    --primary-bg:#c8d8ef; --primary-ink:#080c12;
    --shadow:0 1px 3px rgba(0,0,0,.5),0 6px 20px -8px rgba(0,0,0,.70);
    --shadow-sm:0 1px 2px rgba(0,0,0,.40),0 3px 10px -5px rgba(0,0,0,.55);
    --shadow-top:0 -1px 3px rgba(0,0,0,.40),0 -4px 12px -6px rgba(0,0,0,.55);
    color-scheme:dark;
  }
}
/* ── Modo oscuro forzado por toggle ──────────────────────────── */
:root[data-theme="dark"]{
  --bg:#080c12; --surface:#111827; --surface-2:#1a2233; --ink:#e8ecf2; --ink-2:#aab4c4; --muted:#7c8ea3; --hair:#1e2a3a; --hair-2:#162030;
  --accent:#5b8fdb; --accent-soft:#16233a; --accent-ink:#8db5f0;
  --o1:#4a8fea; --o1-soft:#132238; --o2:#e06020; --o2-soft:#32190a; --o3:#7c8ea3; --o3-soft:#1e2a3a; --o4:#1db368; --o4-soft:#0a2518;
  --good:#1db368; --good-soft:#0a2518; --good-ink:#60d9a0;
  --warn:#e8a020; --warn-soft:#30200a; --warn-ink:#f2c060;
  --critical:#e85555; --critical-soft:#300f0f; --critical-ink:#f09090;
  --good-btn:#178a52; --o1-btn:#3070d0; --o2-btn:#c84c10; --o3-btn:#3d4754; --o4-btn:#178a52;
  --tabs-bg:#05080e; --tabs-ink:#f8fafc; --tabs-muted:rgba(248,250,252,.5); --tabs-active-line:#e8b84b; --tabs-active-bg:rgba(232,184,75,.08);
  --pill-curso-ink:#f2c060; --pill-ok-ink:#60d9a0;
  --primary-bg:#c8d8ef; --primary-ink:#080c12;
  --shadow:0 1px 3px rgba(0,0,0,.5),0 6px 20px -8px rgba(0,0,0,.70);
  --shadow-sm:0 1px 2px rgba(0,0,0,.40),0 3px 10px -5px rgba(0,0,0,.55);
  --shadow-top:0 -1px 3px rgba(0,0,0,.40),0 -4px 12px -6px rgba(0,0,0,.55);
  color-scheme:dark;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
[hidden]{display:none!important}
button,input,select,label{touch-action:manipulation}
input[type=search]{-webkit-appearance:none;appearance:none}
html{-webkit-text-size-adjust:100%;overscroll-behavior-y:contain}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;padding-bottom:84px}
/* Títulos: Source Serif 4 para identidad institucional */
h1{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:20px;margin:0;letter-spacing:-.02em;line-height:1.2}
h2{font-size:11.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin:0}
button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
/* Anillo de foco accesible (WCAG 2.4.7) */
button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
input,select{font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--hair);border-radius:var(--r-sm);padding:8px 10px}
/* Numéricos tabulares — clave para quórum/porcentuales */
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.wrap{max-width:900px;margin:0 auto;padding:0 16px}
/* ---- top summary (sticky) */
.top{position:sticky;top:0;z-index:10;background:var(--surface);border-bottom:1px solid var(--hair);box-shadow:var(--shadow)}
.top .wrap{padding:12px 16px 10px;display:grid;gap:10px}
.titlebar{display:flex;align-items:center;justify-content:space-between;gap:10px}
.titlebar .sub{font-size:12px;color:var(--muted);letter-spacing:.01em}
.iconbtn{width:40px;height:40px;border-radius:var(--r-sm);border:1px solid var(--hair);display:inline-flex;align-items:center;justify-content:center;color:var(--ink-2);background:var(--surface);transition:background-color .15s ease,border-color .15s ease}
.iconbtn svg{transition:transform .2s ease}
.top.compact .iconbtn#btnCollapse svg,.iconbtn[aria-expanded="false"] svg{transform:rotate(-90deg)}
.btn svg{vertical-align:-4px;margin-left:2px}
.iconbtn:hover{background:var(--surface-2)}
.mocion{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
.mocion button{white-space:nowrap;padding:6px 14px;border-radius:999px;border:1px solid var(--hair);font-size:13px;font-weight:500;color:var(--ink-2);background:var(--surface);transition:background-color .15s ease,border-color .15s ease,color .15s ease}
.mocion button[aria-pressed="true"]{background:var(--primary-bg);color:var(--primary-ink);border-color:var(--primary-bg)}
.mocion button.add{border-style:dashed;color:var(--muted)}
/* ── Quórum: números grandes, legibles a un brazo ──────────────── */
.quorum{display:grid;grid-template-columns:1fr auto;gap:4px 12px;align-items:baseline}
.quorum .lab{font-size:12px;color:var(--muted);font-weight:500}
.quorum .val{font-family:"Source Serif 4",Georgia,serif;font-size:17px;font-weight:700;line-height:1;letter-spacing:-.01em}
.qbar{grid-column:1/-1;height:7px;border-radius:4px;background:var(--hair-2);overflow:hidden;position:relative}
.qbar i{position:absolute;left:0;top:0;height:100%;background:var(--good);border-radius:4px}
.qbar i.p{background:var(--warn);opacity:.9}
.qbar b{position:absolute;top:-3px;width:2px;height:13px;background:var(--ink);opacity:.5;left:50%}
.results{display:grid;gap:12px;padding-top:2px}
.res{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;align-items:baseline}
.res .name{font-weight:600;font-size:14px;display:flex;align-items:center;gap:8px;min-width:0}
.res .name span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.res .name i{width:10px;height:10px;border-radius:3px;flex:none}
/* Porcentual grande con Source Serif 4 — número clave */
.res .pct{font-family:"Source Serif 4",Georgia,serif;font-size:20px;font-weight:700;line-height:1;letter-spacing:-.01em}
.res .meta{grid-column:1/-1;font-size:12px;color:var(--muted);display:flex;gap:4px 0;flex-wrap:wrap;align-items:center;margin-top:1px}
.res .meta>span:not(.verdict)+span:not(.verdict)::before{content:'·';margin:0 6px;color:var(--hair)}
.res .meta .verdict{margin-left:auto}
.res .bar{grid-column:1/-1;height:8px;border-radius:4px;background:var(--hair-2);overflow:hidden;position:relative;margin-top:1px}
.res .bar i{display:block;height:100%;border-radius:4px}
.res .bar b{position:absolute;top:-2px;width:2px;height:12px;background:var(--ink);opacity:.45}
.verdict{font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:5px;display:inline-flex;gap:5px;align-items:center;white-space:nowrap;letter-spacing:.01em}
.verdict.ok{background:var(--good-soft);color:var(--good-ink)} .verdict.no{background:var(--surface-2);color:var(--muted)} .verdict.pend{background:var(--warn-soft);color:var(--warn-ink)}
.top.collapsed .results,.top.collapsed .mocion,.top.collapsed .cump{display:none}
.mini{display:none;gap:6px 14px;flex-wrap:wrap;font-size:14px;align-items:center}
.mini b{font-weight:700} .mini i{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px;vertical-align:middle}
.mini .q{color:var(--muted);font-weight:500}
.top.compact .mocion,.top.compact .quorum,.top.compact .results,.top.compact .titlebar,.top.compact .cump{display:none}
.top.compact .mini{cursor:pointer;padding-right:26px;position:relative}
.top.compact .mini::after{content:'';position:absolute;right:4px;top:2px;width:14px;height:14px;background:currentColor;-webkit-mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><path d='M6 9l6 6 6-6'/></svg>") center/contain no-repeat;mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><path d='M6 9l6 6 6-6'/></svg>") center/contain no-repeat;color:var(--muted)}
.top.compact .mini{display:flex}
.top.compact .titlebar h1{font-size:15px}
.top.compact .wrap{padding-top:8px;padding-bottom:8px;gap:4px}
.syncdot{width:9px;height:9px;border-radius:50%;background:var(--hair);margin-right:4px;flex:none}
.syncdot.ok{background:var(--good)} .syncdot.err{background:var(--critical)} .syncdot.busy{background:var(--warn)}
/* ---- toolbar */
.toolbar{display:flex;gap:8px;align-items:center;padding:14px 0 8px;flex-wrap:wrap}
.toolbar input[type=search]{flex:1;min-width:160px}
.toolbar select{font-size:13.5px}
.toolbar .count{font-size:12.5px;color:var(--muted);margin-left:auto}
/* ---- unit rows */
.list{display:grid;gap:8px}
.unit{background:var(--surface);border:1px solid var(--hair);border-radius:var(--r-md);padding:12px 14px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px 10px;align-items:center;transition:border-color .15s ease;box-shadow:var(--shadow-sm)}
/* Borde izquierdo semántico: presente = verde, poder = ámbar */
.unit.present{border-left:3px solid var(--good);padding-left:13px}
.unit.poder-only{border-left:3px solid var(--warn);padding-left:13px}
.unit.absent{opacity:.72}
.unit .who{min-width:0}
.unit .uf{font-size:12px;color:var(--muted);font-weight:500;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.unit .uf b{color:var(--ink-2);font-weight:600;font-size:13px}
.unit .prop{font-weight:600;font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink);margin-top:2px}
/* Coeficiente: tabular, Source Serif para dignidad numérica */
.unit .coef{font-family:"Source Serif 4",Georgia,serif;font-size:14px;font-weight:700;color:var(--ink-2);white-space:nowrap;font-variant-numeric:tabular-nums}
.unit .acts{grid-column:1/-1;display:grid;gap:6px}
.unit .acts .r1,.unit .acts .r2{display:flex;gap:6px;align-items:stretch}
.unit .acts .r1 .tog{flex:1 1 0}
.unit .acts .r1 .tog.multi{flex:0 0 auto}
.unit .acts .r2 .tog{flex:1 1 0;text-align:center;padding-left:6px;padding-right:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tog{padding:8px 12px;border-radius:var(--r-sm);border:1px solid var(--hair);font-size:13px;font-weight:600;color:var(--ink-2);background:var(--surface);min-height:38px;transition:background-color .15s ease,border-color .15s ease,color .15s ease;position:relative}
.tog[aria-pressed="true"]::before{content:'';display:inline-block;width:13px;height:13px;margin-right:5px;vertical-align:-2px;background:currentColor;-webkit-mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'><path d='M5 12.5l4.5 4.5L19 7.5'/></svg>") center/contain no-repeat;mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'><path d='M5 12.5l4.5 4.5L19 7.5'/></svg>") center/contain no-repeat}
@media (hover:hover){.tog:not([aria-pressed="true"]):not(:disabled):hover{background:var(--surface-2);border-color:var(--muted)} .btn:hover{background:var(--surface-2)} .chipu:not(.on):not(.poder):hover{border-color:var(--muted)}}
.tog[aria-pressed="true"]{color:#fff;border-color:transparent}
.tog.pres[aria-pressed="true"]{background:var(--good-btn)}
.tog.poder[aria-pressed="true"]{background:#96580e;color:#fff}
.tog.o1[aria-pressed="true"]{background:var(--o1-btn)} .tog.o2[aria-pressed="true"]{background:var(--o2-btn)} .tog.o3[aria-pressed="true"]{background:var(--o3-btn)} .tog.o4[aria-pressed="true"]{background:var(--o4-btn)}
.tog:disabled{opacity:.38;cursor:not-allowed}
.tog.multi{border-style:dashed;color:var(--muted);font-weight:500;font-size:12px}
.sep{width:1px;height:22px;background:var(--hair);margin:0 2px}
.poderinput{grid-column:1/-1;display:flex;gap:6px;align-items:center;font-size:13px;color:var(--ink-2)}
.poderinput input{flex:1;padding:8px 10px;font-size:16px}
/* ---- pasar lista */
.roll{display:grid;gap:16px}
.roll .floor{display:grid;gap:8px}
.roll .floor h2{padding:0 2px}
.roll .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:6px}
.chipu{display:grid;grid-template-columns:minmax(0,1fr) auto;border:1px solid var(--hair);border-radius:var(--r-md);background:var(--surface);overflow:hidden;min-height:54px;transition:background-color .15s ease,border-color .15s ease;box-shadow:var(--shadow-sm)}
.chipu.on .main b::before{content:'';display:inline-block;width:12px;height:12px;margin-right:4px;vertical-align:-1px;background:#fff;-webkit-mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'><path d='M5 12.5l4.5 4.5L19 7.5'/></svg>") center/contain no-repeat;mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'><path d='M5 12.5l4.5 4.5L19 7.5'/></svg>") center/contain no-repeat}
.chipu .main{text-align:left;padding:8px 10px;min-width:0;display:grid;gap:1px}
.chipu .main b{font-size:14px}
.chipu .main span{font-size:12px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chipu .pd{border-left:1px solid var(--hair);padding:0 9px;font-size:11px;font-weight:700;color:var(--muted);letter-spacing:.04em}
.chipu.on{background:var(--good-btn);border-color:var(--good-btn)}
.chipu.on .main b,.chipu.on .main span{color:#fff}
.chipu.on .pd{color:#fff;border-color:rgba(255,255,255,.35)}
.chipu.poder{background:#96580e;border-color:#96580e}
.chipu.poder .main b,.chipu.poder .main span{color:#fff}
.chipu.poder .pd{color:#fff;border-color:rgba(255,255,255,.35)}
.rollhead{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 0 4px;flex-wrap:wrap}
.rollhead .note{flex:1}

/* ---- pestañas y vistas */
.tabs{position:sticky;top:0;z-index:12;background:var(--tabs-bg);color:var(--tabs-ink);display:flex;align-items:stretch;gap:0;overflow-x:auto;scrollbar-width:none;padding:0 6px;box-shadow:0 2px 8px rgba(0,0,0,.25)}
/* Pestañas: tab activa con línea dorada institucional + leve wash */
.tabs button{flex:1 0 auto;min-width:64px;padding:13px 10px 11px;font-size:12.5px;font-weight:600;color:var(--tabs-muted);border-bottom:3px solid transparent;white-space:nowrap;transition:color .15s ease,border-color .15s ease,background-color .15s ease;letter-spacing:.01em}
.tabs button[aria-selected="true"]{color:var(--tabs-ink);border-bottom-color:var(--tabs-active-line);background:var(--tabs-active-bg)}
.tabs .brand{flex:0 0 auto;align-self:center;font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:15px;padding:0 12px 0 6px;color:var(--tabs-ink);white-space:nowrap;letter-spacing:-.01em}
.top{top:48px}
.view{display:grid;gap:16px;padding:16px 0 28px}
/* Títulos de sección con Source Serif 4 — identidad institucional */
.view h2.sec{font-family:"Source Serif 4",Georgia,serif;font-size:22px;font-weight:600;letter-spacing:-.02em;text-transform:none;color:var(--ink);line-height:1.2}
.lead{color:var(--ink-2);font-size:15px;max-width:72ch;line-height:1.6}
/* Tarjetas: borde sutil + sombra leve — aspecto de documento */
.card{background:var(--surface);border:1px solid var(--hair);border-radius:var(--r-md);padding:16px 18px;display:grid;gap:12px;box-shadow:var(--shadow-sm)}
.card h3{margin:0;font-size:17px;line-height:1.3;font-weight:600;color:var(--ink)}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:3px 9px;border-radius:999px;background:var(--surface-2);color:var(--ink-2)}
.pill.curso{background:var(--warn-soft);color:var(--pill-curso-ink)} .pill.tratado{background:var(--good-soft);color:var(--pill-ok-ink)} .pill.pend{background:var(--surface-2)}
.pt-head{display:flex;gap:10px;align-items:flex-start;justify-content:space-between}
/* Número de punto de agenda: serif grande, muted — numeración editorial */
.pt-num{font-family:"Source Serif 4",Georgia,serif;font-size:30px;font-weight:600;color:var(--hair);line-height:1;min-width:36px}
.kv{display:grid;gap:6px;font-size:14.5px} .kv b{color:var(--ink);font-weight:600} .kv p{color:var(--ink-2);margin:0;line-height:1.5}
.moc-res{display:grid;gap:6px;border-top:1px solid var(--hair-2);padding-top:12px}
.moc-res .row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;font-size:14px;align-items:center}
.moc-res .row i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:6px}
.moc-res .bar{height:6px;border-radius:3px;background:var(--hair-2);overflow:hidden}.moc-res .bar b{display:block;height:100%}
.actions{display:flex;gap:8px;flex-wrap:wrap}
.btn.sm{padding:8px 14px;font-size:13.5px;min-height:40px}
.modbar{display:flex;align-items:center;justify-content:space-between;gap:10px;background:var(--surface-2);border:1px dashed var(--hair);border-radius:var(--r-md);padding:10px 14px;font-size:14px}
.modbar b{color:var(--ink)}
.mod-only{display:none} body.mod .mod-only{display:initial} body.mod .mod-only.actions,body.mod .mod-only.row{display:flex}
.oradores{display:grid;gap:6px} .orador{display:flex;justify-content:space-between;align-items:center;gap:10px;background:var(--surface-2);border-radius:var(--r-sm);padding:10px 12px;font-size:15px}
.orador .n{font-weight:700;color:var(--muted);min-width:22px;font-family:"Source Serif 4",Georgia,serif}
.q{display:grid;gap:8px} .q .tema{font-size:11.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.q p.txt{font-size:15.5px;line-height:1.5;color:var(--ink)} .q .doc{font-size:13px;color:var(--ink-2);padding:8px 12px;background:var(--surface-2);border-radius:var(--r-sm);border-left:3px solid var(--hair)}
.q .resp{border-left:3px solid var(--good);padding:8px 12px;font-size:14.5px;background:var(--good-soft);border-radius:0 var(--r-sm) var(--r-sm) 0;color:var(--good-ink)}
.q textarea{width:100%;min-height:70px;font:inherit;font-size:16px;border:1px solid var(--hair);border-radius:var(--r-sm);padding:10px;background:var(--surface);color:var(--ink)}
.prop{display:grid;gap:8px}
.prop .stat{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}
.prop .stat div{background:var(--surface-2);border-radius:var(--r-sm);padding:10px 12px;font-size:13px;color:var(--ink-2);border:1px solid var(--hair-2)}
.prop .stat b{display:block;font-family:"Source Serif 4",Georgia,serif;font-size:22px;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums;margin-bottom:2px}
.form{display:grid;gap:10px} .form label{display:grid;gap:4px;font-size:13.5px;color:var(--ink-2);font-weight:500}
.form input,.form select,.form textarea{font:inherit;font-size:16px;padding:10px 12px;border:1px solid var(--hair);border-radius:var(--r-sm);background:var(--surface);color:var(--ink);width:100%}
.objlist{display:grid;gap:6px} .obj{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;background:var(--surface-2);border-radius:var(--r-sm);padding:8px 12px;font-size:14px}
.docs a{color:var(--accent-ink);font-weight:600;text-decoration-thickness:1.5px;text-underline-offset:2px}
pre.doc{white-space:pre-wrap;font:inherit;font-size:14.5px;line-height:1.55;color:var(--ink-2);margin:0}

/* ================================================================
   Pestaña Encargado y Reglamento — contenedor .doc (documento largo)
   ui-ux-pro-max v2: jerarquía editorial institucional, móvil primero
   ================================================================ */

/* Contenedor raíz: ancho de lectura cómodo, espacio generoso */
div.doc{
  max-width:68ch;          /* ~65–70 chars/línea: punto óptimo de lectura */
  font-size:15px;
  line-height:1.75;
  color:var(--ink-2);
}
@media (max-width:640px){
  div.doc{ font-size:16px; line-height:1.7; }
}

/* --- Encabezados dentro de .doc ---
   h2 → sección principal: Source Serif + acento
   h3 → subsección: Inter 600 + ink
   h4 → nivel terciario: Inter 500 + muted
   (El renderer suma +1 al nivel, así que ## → h3, ### → h4, #### → h5)
*/
div.doc h2{
  font-family:"Source Serif 4",Georgia,serif;
  font-size:21px; font-weight:600; letter-spacing:-.02em;
  text-transform:none; color:var(--ink);
  margin:2rem 0 .5rem; line-height:1.25;
  border-bottom:2px solid var(--accent-soft);
  padding-bottom:.35rem;
}
div.doc h3{
  font-family:Inter,system-ui,sans-serif;
  font-size:16px; font-weight:700; letter-spacing:0;
  color:var(--accent-ink); text-transform:none;
  margin:1.6rem 0 .35rem; line-height:1.3;
}
div.doc h4{
  font-family:Inter,system-ui,sans-serif;
  font-size:14px; font-weight:600; letter-spacing:.03em;
  text-transform:uppercase; color:var(--muted);
  margin:1.4rem 0 .3rem; line-height:1.3;
}
div.doc h5{
  font-family:Inter,system-ui,sans-serif;
  font-size:13px; font-weight:600; letter-spacing:.04em;
  text-transform:uppercase; color:var(--muted);
  margin:1.2rem 0 .25rem; line-height:1.3;
}
@media (max-width:640px){
  div.doc h2{ font-size:19px; margin-top:1.75rem; }
  div.doc h3{ font-size:15.5px; }
}

/* Primer encabezado: menos espacio arriba */
div.doc>h2:first-child,
div.doc>h3:first-child{
  margin-top:.5rem;
}

/* --- Párrafos --- */
div.doc p{
  margin:.65rem 0;
  color:var(--ink-2);
}

/* --- Blockquotes: formulaciones sugeridas y preguntas clave --- */
div.doc blockquote{
  margin:1.1rem 0;
  padding:.75rem 1rem .75rem 1.1rem;
  border-left:4px solid var(--accent);
  background:var(--accent-soft);
  border-radius:0 var(--r-sm) var(--r-sm) 0;
  color:var(--accent-ink);
  font-style:normal;
}
div.doc blockquote p{
  margin:.3rem 0;
  color:var(--accent-ink);
  font-size:14.5px;
  line-height:1.6;
}
div.doc blockquote p:first-child{ margin-top:0; }
div.doc blockquote p:last-child{ margin-bottom:0; }

/* --- Listas: preguntas numeradas, ventajas/desventajas --- */
div.doc ol,
div.doc ul{
  margin:.65rem 0;
  padding-left:1.6em;
}
div.doc ol{ list-style:decimal; }
div.doc ul{ list-style:disc; }
div.doc li{
  margin-bottom:.55rem;
  line-height:1.65;
  color:var(--ink-2);
}
div.doc li:last-child{ margin-bottom:0; }

/* --- Negritas generadas por marked (<strong>) --- */
div.doc strong{
  font-weight:700;
  color:var(--ink);
}

/* --- pre: matriz y arte-ASCII — no rompe el ancho en móvil --- */
div.doc pre.doc,
div.doc pre{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12.5px;
  line-height:1.55;
  white-space:pre;           /* preservar alineación */
  overflow-x:auto;           /* scroll horizontal en móvil */
  background:var(--surface-2);
  border:1px solid var(--hair);
  border-radius:var(--r-sm);
  padding:.75rem 1rem;
  margin:.9rem 0;
  color:var(--ink-2);
  -webkit-overflow-scrolling:touch;
}
div.doc pre code{
  font:inherit;
  background:none;
  border:none;
  padding:0;
}
@media (max-width:640px){
  div.doc pre.doc,
  div.doc pre{ font-size:11.5px; padding:.6rem .75rem; }
}

/* --- Separadores hr: sutiles, con margen generoso --- */
div.doc hr{
  border:none;
  border-top:1px solid var(--hair);
  margin:1.75rem 0;
}

/* --- details / summary: buscador e índice dentro del contenedor --- */
details.card summary{
  cursor:pointer;
  font-size:14px;
  font-weight:600;
  color:var(--accent-ink);
  padding:2px 0;
  list-style:none;            /* quita triángulo nativo en Safari */
  -webkit-appearance:none;
  user-select:none;
}
details.card summary::-webkit-details-marker{ display:none; }
details.card summary::before{
  content:'▶ ';
  font-size:10px;
  display:inline-block;
  transition:transform .15s ease;
  color:var(--accent);
}
details[open].card summary::before{ transform:rotate(90deg); }
details.card[open]{ gap:12px; }

/* --- details de texto completo de artículo (normativa) --- */
.norm-texto-details{
  margin-top:8px;
}
.norm-texto-details summary{
  cursor:pointer;
  font-size:13px;
  font-weight:600;
  color:var(--accent-ink);
  list-style:none;
  -webkit-appearance:none;
  user-select:none;
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:4px 0;
}
.norm-texto-details summary::-webkit-details-marker{ display:none; }
.norm-texto-details summary::before{
  content:'▶';
  font-size:10px;
  display:inline-block;
  transition:transform .15s ease;
  color:var(--accent);
  flex:none;
}
.norm-texto-details[open] summary::before{ transform:rotate(90deg); }
.norm-texto-body{
  margin-top:10px;
  padding:12px 14px;
  background:var(--surface-2);
  border-left:3px solid var(--accent);
  border-radius:0 var(--r-sm) var(--r-sm) 0;
  font-size:13.5px;
  line-height:1.7;
  color:var(--ink-2);
}
.norm-texto-body p{
  margin:.55rem 0;
}
.norm-texto-body p:first-child{ margin-top:0; }
.norm-texto-body p:last-child{ margin-bottom:0; }

/* Buscador y details de índice en pestaña encargado/reglamento */
#encBuscar,#regBuscar{
  display:block;
  width:100%;
  padding:10px 12px;
  font-size:16px;
  border:1px solid var(--hair);
  border-radius:var(--r-sm);
  background:var(--surface);
  color:var(--ink);
  margin-bottom:10px;
  box-sizing:border-box;
}
#encIndice,#regIndice{
  margin-bottom:12px;
}
#encIndiceNav,#regIndiceNav{
  display:grid;
  gap:4px;
  padding-top:8px;
}
#encIndiceNav a,#regIndiceNav a{
  color:var(--accent-ink);
  text-decoration:none;
  font-size:13.5px;
  font-weight:500;
  padding:4px 2px;
  border-bottom:1px solid var(--hair-2);
  display:block;
}
#encIndiceNav a:hover,#regIndiceNav a:hover{
  color:var(--accent);
}

.vhide{display:none!important}
@media (max-width:640px){ .tabs button{font-size:12px;padding:12px 7px 10px;min-width:52px} .tabs .brand{display:none} .view h2.sec{font-size:19px} .wrap{padding:0 12px} }

/* ---- bottom bar */
.bottom{position:fixed;left:0;right:0;bottom:0;z-index:10;background:var(--surface);border-top:1px solid var(--hair);padding:8px 16px calc(8px + env(safe-area-inset-bottom));box-shadow:var(--shadow-top)}
.bottom .wrap{display:flex;gap:8px;justify-content:center;padding:0}
.bottom .btn{flex:1 1 0;white-space:nowrap;padding-left:8px;padding-right:8px}
.btn{padding:9px 14px;border-radius:var(--r-sm);border:1px solid var(--hair);font-size:13.5px;font-weight:600;background:var(--surface);color:var(--ink-2);transition:background-color .15s ease,border-color .15s ease,opacity .15s ease}
.btn:disabled{opacity:.38;cursor:progress}
.btn.primary{background:var(--primary-bg);color:var(--primary-ink);border-color:var(--primary-bg)}
.btn.danger{color:var(--critical-ink)}
/* ---- dialog */
dialog{border:0;border-radius:var(--r-lg);padding:0;max-width:min(560px,94vw);width:100%;background:var(--surface);color:var(--ink);box-shadow:var(--shadow);margin:6vh auto auto;max-height:86vh;overflow:auto}
dialog::backdrop{background:rgba(5,8,14,.6)}
dialog .body{padding:20px;display:grid;gap:14px;overflow:hidden}
dialog input,dialog select,dialog textarea{width:100%;min-width:0;max-width:100%;box-sizing:border-box}
dialog label>*{min-width:0}
dialog h3{margin:0;font-size:17px;font-weight:600;color:var(--ink)}
dialog label{display:grid;gap:4px;font-size:13px;color:var(--ink-2);font-weight:500}
dialog .row{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}
dialog textarea{font:inherit;font-size:12.5px;width:100%;min-height:220px;border:1px solid var(--hair);border-radius:var(--r-sm);padding:10px;background:var(--surface-2);color:var(--ink);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;line-height:1.5}
.note{font-size:12.5px;color:var(--muted);line-height:1.5}
.opts{display:grid;gap:6px}
.opts .opt{display:grid;grid-template-columns:14px minmax(0,1fr) auto;gap:8px;align-items:center}
.opts .opt input{min-width:0}
.opts .opt i{width:12px;height:12px;border-radius:3px}
.toast{position:fixed;left:50%;bottom:84px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:9px 16px;border-radius:var(--r-sm);font-size:13px;font-weight:500;display:none;z-index:20;box-shadow:var(--shadow);white-space:nowrap}

/* ---- teléfono: todo más grande y claro (arm's-length readability) */
@media (max-width:640px){
  body{font-size:17px}
  h1{font-size:19px}
  .titlebar .sub{font-size:13px}
  /* Quórum muy legible: números serif grandes */
  .quorum .lab{font-size:14px} .quorum .val{font-size:26px}
  .qbar{height:9px}
  /* Porcentuales de resultados: serif grande */
  .res .name{font-size:16px} .res .pct{font-size:28px} .res .meta{font-size:13.5px} .res .bar{height:10px}
  .verdict{font-size:12.5px;padding:4px 10px}
  .mocion button{font-size:14px;padding:8px 14px}
  .toolbar input[type=search],.toolbar select{font-size:16px;padding:11px 12px;min-height:46px}
  .unit{padding:12px 12px}
  .unit .uf{font-size:13.5px} .unit .uf b{font-size:15px} .unit .prop{font-size:18px} .unit .coef{font-size:15px}
  .tog{padding:11px 10px;font-size:15.5px;min-height:50px;border-radius:8px}
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
/* ---- panel de cumplimiento del reglamento ──────────────────────
   Compacto por defecto; en móvil colapsable vía .cump-collapsed
   El header muestra un resumen (N ok / N total) cuando está colapsado
   ----------------------------------------------------------------- */
.cump{display:grid;gap:3px;padding:6px 0 2px}
.cump-header{display:flex;align-items:center;justify-content:space-between;gap:8px;padding-bottom:4px;border-bottom:1px solid var(--hair-2);cursor:default}
.cump-header h2{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:700;margin:0}
/* Botón colapsar (solo visible en móvil) */
.cump-toggle{display:none;font-size:11px;color:var(--accent-ink);background:none;border:0;padding:0;cursor:pointer;font-weight:600;text-decoration:underline;text-underline-offset:2px;white-space:nowrap}
.cump-summary{display:none;font-size:11.5px;color:var(--muted);font-weight:500}
.cump-row{display:grid;grid-template-columns:auto 1fr auto;gap:5px 8px;align-items:center;font-size:12.5px;padding:3px 0;min-height:24px}
.cump-row .cump-ico{font-size:13px;width:18px;text-align:center;flex:none;font-style:normal}
.cump-row .cump-lbl{color:var(--ink-2);min-width:0;line-height:1.4}
.cump-row .cump-actions{display:flex;gap:6px;align-items:center}
.cump-row .cump-lnk{font-size:11px;color:var(--accent-ink);background:none;border:0;padding:0;cursor:pointer;white-space:nowrap;text-decoration:underline;text-underline-offset:2px}
.cump-row .cump-tog{font-size:11px;padding:2px 8px;border-radius:4px;border:1px solid var(--hair);background:var(--surface-2);color:var(--ink-2);cursor:pointer;white-space:nowrap;transition:background-color .12s ease}
.cump-row .cump-tog:hover{background:var(--hair-2)}
/* Estados semánticos con color + símbolo (nunca solo color) */
.cump-row.ok .cump-ico{color:var(--good)}
.cump-row.no .cump-ico{color:var(--critical-ink)}
.cump-row.pend .cump-ico{color:var(--muted)}
/* Fila alerta: fondo tenue para urgencia visual */
.cump-row.no{background:none}
@media (max-width:640px){
  /* En móvil el panel es colapsable */
  .cump-toggle{display:inline}
  /* Cuando está colapsado: ocultar las filas, mostrar resumen */
  .cump.cump-collapsed .cump-row{display:none}
  .cump.cump-collapsed .cump-summary{display:inline}
  .cump-row{font-size:13px} .cump-row .cump-lnk{font-size:12px} .cump-row .cump-tog{font-size:12px;padding:3px 9px}
  .cump-header{cursor:pointer}
}
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
  <button role="tab" data-tab="reglamento" aria-selected="false">Reglamento</button>
  <button role="tab" data-tab="normativa" aria-selected="false">Normativa</button>
  <button role="tab" data-tab="encargado" aria-selected="false">Encargado</button>
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
    <div class="cump" id="cumplimiento"></div>
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
  <p class="lead">Preguntas para la administración de esta asamblea. Las respuestas que dé quedan registradas. Para las preguntas sobre la continuidad del encargado, ver la pestaña Encargado.</p>
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
<div class="wrap view" id="view-reglamento">
  <h2 class="sec">Reglamento de copropiedad</h2>
  <input id="regBuscar" type="search" placeholder="Buscar en el reglamento…" aria-label="Buscar en el reglamento" style="width:100%;padding:10px;font-size:16px;margin-bottom:10px">
  <details id="regIndice" class="card"><summary>Índice de artículos</summary><nav id="regIndiceNav"></nav></details>
  <div id="regTexto" class="doc"></div>
</div>
<div class="wrap view" id="view-normativa">
  <h2 class="sec">Normativa de referencia</h2>
  <p class="lead">Marco legal aplicable a la asamblea. Cada ítem resume la norma y enlaza al texto oficial; verificá en la fuente ante cualquier duda.</p>
  <div id="normativaList" style="display:grid;gap:12px"></div>
</div>
<div class="wrap view" id="view-encargado">
  <h2 class="sec">Continuidad del encargado</h2>
  <p class="lead">Preguntas para consultar a la Administración y al Consejo antes de decidir sobre la continuidad del encargado. Buscá por tema o usá el índice.</p>
  <input id="encBuscar" type="search" placeholder="Buscar…" aria-label="Buscar en el documento del encargado" style="width:100%;padding:10px;font-size:16px;margin-bottom:10px">
  <details id="encIndice" class="card"><summary>Índice</summary><nav id="encIndiceNav"></nav></details>
  <div id="encTexto" class="doc"></div>
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
<script>__MARKED__</script>
<script>__LOGICA__</script>
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
const fresh = ()=>({ presentes:{}, poderes:{}, activa:0, agenda:{}, palabra:[], respuestas:{}, objeciones:{}, cumplimiento:{ presidentePropietario:null, dosFirmantes:null, antelacionOk:null }, mociones:[ { titulo:'Que Ramón Gonzalez continúe como encargado', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} }, { titulo:'Aprobar el reglamento interno con régimen de multas', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} }, { titulo:'Constituir el tribunal de multas', opciones:['A favor','En contra','Abstención'], regla:'abs', votos:{} } ] });
let S = fresh();
try { const raw = localStorage.getItem(KEY); if(raw){ const p = JSON.parse(raw); if(p && p.mociones && p.mociones.length) S = p; } } catch(e){}
if(!S.cumplimiento) S.cumplimiento = { presidentePropietario:null, dosFirmantes:null, antelacionOk:null };
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
function verdict(m, c, o){ return CTLogica.veredicto(m.regla, o, {N:N, totalPct:TOTAL_PCT}, {partN:c.partN, partPct:c.partPct}); }

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
  renderCumplimiento(c);
}

// ---------- panel de cumplimiento del reglamento (art. 25 del Reglamento de Copropiedad)
function setCumplimiento(k, v){ S.cumplimiento[k]=v; sync.send({t:'cumplimiento', k, v}); save(); renderCumplimiento(); }
function renderCumplimiento(c){
  if(!c){ const m=M(); c=compute(m); }
  const cum = S.cumplimiento || {};
  // Checks automáticos
  const partPct = c.partPct;
  const quorumOk = partPct > TOTAL_PCT/2;
  const excedidos = CTLogica.mandatariosExcedidos(S.poderes, UNITS);
  const poderOk = excedidos.length === 0;
  // Admin no vota: ✗ si alguna UF admin tiene voto en alguna moción
  const adminUfs = UNITS.filter(u=>u.admin).map(u=>u.uf);
  const adminVota = S.mociones.some(m=>adminUfs.some(uf=>m.votos[uf]!=null));
  // Mayoría moción activa
  const ma = M(); const ca = (c.partPct!=null && S.mociones[S.activa]===ma) ? c : compute(ma);
  const winOpt = ca.opts.filter(o=>!o.abst).sort((a,b)=>b.pct-a.pct)[0];
  const mocVerdict = winOpt ? CTLogica.veredicto(ma.regla, winOpt, {N:N, totalPct:TOTAL_PCT}, {partN:ca.partN, partPct:ca.partPct}) : null;
  const mocAprobada = mocVerdict && mocVerdict.ok;
  const mocVotada = ca.opts.reduce((s,o)=>s+o.n,0)>0;
  // Checks manuales: null=pendiente, true=✓, false=✗
  function icopar(v){ return v===true?'✓':v===false?'✗':'—'; }
  function clspar(v){ return v===true?'ok':v===false?'no':'pend'; }
  function nextVal(v){ return v===null?true:v===true?false:null; }
  const rows = [
    // Automáticos
    { auto:true, cls:quorumOk?'ok':'no', ico:quorumOk?'✓':'✗',
      lbl:'Quórum (art. 25 e): '+fp(partPct)+' de presentes'+(!quorumOk?' — necesita más del '+fp(TOTAL_PCT/2):''),
      art:'quórum' },
    { auto:true, cls:poderOk?'ok':'no', ico:poderOk?'✓':'✗',
      lbl:'Tope de poderes (art. 25 h)'+(poderOk?'':': excede — '+excedidos.map(x=>esc(x)).join(', ')),
      art:'Representación' },
    { auto:true, cls:adminVota?'no':'ok', ico:adminVota?'✗':'✓',
      lbl:'Admin no vota (art. 25 c)'+(adminVota?' — hay voto del administrador':''),
      art:'administrador' },
    { auto:true, cls:!mocVotada?'pend':mocAprobada?'ok':'no', ico:!mocVotada?'—':mocAprobada?'✓':'✗',
      lbl:'Mayoría moción activa (art. 25 g)'+(mocVotada&&!mocAprobada?' — no alcanza':''),
      art:'mayoría' },
    // Manuales
    { auto:false, k:'presidentePropietario', lbl:'Presidente de la asamblea es propietario (art. 25 b)', art:'presidente' },
    { auto:false, k:'dosFirmantes',          lbl:'Acta firmada por 2 propietarios (art. 25 i)',         art:'firma' },
    { auto:false, k:'antelacionOk',          lbl:'Convocatoria con antelación debida (art. 25 d)',      art:'convocatoria' },
  ];
  // Resumen compacto para el header colapsado: "N ✓ / N total"
  const allRows = rows.map(r => r.auto ? r.cls : clspar(cum[r.k]));
  const okCount = allRows.filter(s=>s==='ok').length;
  const noCount = allRows.filter(s=>s==='no').length;
  const summaryTxt = noCount > 0
    ? `${noCount} incumplimiento${noCount>1?'s':''} · ${okCount}/${allRows.length} ✓`
    : `${okCount}/${allRows.length} ✓`;
  const summaryColor = noCount > 0 ? 'var(--critical-ink)' : 'var(--good-ink)';
  // Preservar estado colapsado previo
  const prevCollapsed = ($('#cumplimiento')||{}).classList && $('#cumplimiento').classList.contains('cump-collapsed');
  let html = `<div class="cump-header"><h2>Cumplimiento del reglamento</h2><span class="cump-summary" style="color:${summaryColor}">${summaryTxt}</span><button class="cump-toggle" aria-label="Mostrar/ocultar cumplimiento" onclick="toggleCump()">${prevCollapsed?'ver detalle':'ocultar'}</button></div>`;
  for(const r of rows){
    if(r.auto){
      html += `<div class="cump-row ${r.cls}"><span class="cump-ico">${r.ico}</span><span class="cump-lbl">${r.lbl}</span><span class="cump-actions"><button class="cump-lnk" onclick="irAReglamento('${r.art}')">art.</button></span></div>`;
    } else {
      const v = cum[r.k]; const cls=clspar(v); const ico=icopar(v);
      html += `<div class="cump-row ${cls}"><span class="cump-ico">${ico}</span><span class="cump-lbl">${r.lbl}</span><span class="cump-actions"><button class="cump-tog mod-only" onclick="setCumplimiento('${r.k}', ${JSON.stringify(nextVal(v))})">cambiar</button><button class="cump-lnk" onclick="irAReglamento('${r.art}')">art.</button></span></div>`;
    }
  }
  $('#cumplimiento').innerHTML = html;
  if(prevCollapsed) $('#cumplimiento').classList.add('cump-collapsed');
}
function toggleCump(){
  const el = $('#cumplimiento');
  const collapsed = el.classList.toggle('cump-collapsed');
  const btn = el.querySelector('.cump-toggle');
  if(btn) btn.textContent = collapsed ? 'ver detalle' : 'ocultar';
}

// ---------- render list
function rowHTML(u){
  const m = M(); const p=!!S.presentes[u.uf], pd=!!S.poderes[u.uf], part=p||pd; const v=m.votos[u.uf];
  const same = UNITS.filter(x=>x.prop===u.prop).length;
  const unitCls = p ? 'present' : (pd ? 'poder-only' : 'absent');
  return `<div class="unit ${unitCls}" data-uf="${u.uf}">
    <div class="who"><div class="uf"><b>${esc(u.piso)}</b><span>UF ${u.uf}</span>${u.tipo==='Cochera'?'<span>cochera</span>':''}${same>1?`<span title="Este propietario tiene ${same} unidades">${same} unidades</span>`:''}</div><div class="prop">${esc(u.prop)}</div></div>
    <div class="coef num">${fp(u.pct)}</div>
    <div class="acts">
      <div class="r1"><button class="tog pres" data-act="pres" aria-pressed="${p}">Presente</button><button class="tog poder" data-act="poder" aria-pressed="${pd}">Poder</button>${same>1?`<button class="tog multi" data-act="multi" title="Aplicar presencia y voto a las ${same} unidades de ${esc(u.prop)}">× ${same}</button>`:''}</div>
      <div class="r2">${m.opciones.map((o,i)=>`<button class="tog ${COLORS[i%4]}" data-act="vote" data-i="${i}" aria-pressed="${v===i}" ${part?'':'disabled'}>${esc(o)}</button>`).join('')}</div>
    </div>
    ${pd?(()=>{
      const mandActual = S.poderes[u.uf];
      const esTercero = typeof mandActual === 'string' && mandActual.startsWith('tercero:');
      const mandLabel = esTercero ? mandActual.slice(8) : (typeof mandActual === 'string' ? mandActual : '');
      const presentes = UNITS.filter(x => S.presentes[x.uf] && !x.admin);
      const opsProp = presentes.filter(x => x.prop !== u.prop).map(x => `<option value="${esc(x.prop)}" ${mandActual===x.prop?'selected':''}>${esc(x.prop)}</option>`);
      const contador = typeof mandActual === 'string' ? ` <span class="note" style="margin-left:4px">(representa ${CTLogica.contarRepresentados(mandActual, S.poderes, UNITS)}/5)</span>` : '';
      return `<div class="poderinput"><label for="poder-${u.uf}">Representado por${contador}</label><select id="poder-${u.uf}" data-act="poderSel"><option value="">— sin asignar —</option>${opsProp.join('')}<option value="tercero" ${esTercero?'selected':''}>Tercero con carta poder…</option></select>${esTercero?`<span class="note" style="margin-left:6px">${esc(mandLabel)}</span>`:''}</div>`;
    })():''}
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
  if(b.dataset.act==='rpres'){ setPresent(u, !S.presentes[uf]); save(); renderTop(); renderRoll(); }
  else {
    if(S.poderes[uf]){ setPoder(u, null); save(); renderTop(); renderRoll(); }
    else {
      // Marcar primero como poder pendiente, luego pedir mandatario en la vista lista
      S.poderes[uf]=true; delete S.presentes[uf]; sync.send({t:'poder', uf, v:true}); save(); renderTop(); renderRoll();
      toast('Poder marcado. Completá el mandatario en la tarjeta de la unidad.');
    }
  }
});
$('#btnLista').addEventListener('click', ()=>setMode(mode==='lista'?'votar':'lista'));
function renderAll(){ renderTop(); if(mode==='lista') renderRoll(); else renderList(); }

// ---------- actions
function setPresent(u, val){ if(val){ S.presentes[u.uf]=true; delete S.poderes[u.uf]; } else { delete S.presentes[u.uf]; if(!S.poderes[u.uf]) for(const m of S.mociones) delete m.votos[u.uf]; } sync.send({t:'presente', uf:u.uf, v:!!val}); }
function setPoder(u, mandatario){
  if(mandatario){
    const r = CTLogica.puedeAsignarMandatario(mandatario, u.uf, S.poderes, UNITS);
    if(!r.ok){
      const el=$('#toast'); el.innerHTML=esc(r.motivo)+' <button onclick="irAReglamento(\'Representación\')" style="background:none;border:0;color:inherit;text-decoration:underline;cursor:pointer;font:inherit;padding:0">Ver art. 25 h</button>';
      el.style.display='block'; clearTimeout(tt); tt=setTimeout(()=>el.style.display='none',4000);
      return;
    }
    S.poderes[u.uf]=mandatario; delete S.presentes[u.uf];
  } else { delete S.poderes[u.uf]; if(!S.presentes[u.uf]) for(const m of S.mociones) delete m.votos[u.uf]; }
  sync.send({t:'poder', uf:u.uf, v:mandatario||false});
}
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
$('#list').addEventListener('change', e=>{
  const sel=e.target.closest('select[data-act="poderSel"]'); if(!sel) return;
  const uf=+sel.closest('.unit').dataset.uf; const u=UNITS.find(x=>x.uf===uf);
  const val=sel.value;
  if(!val){ setPoder(u, null); save(); renderTop(); renderRow(uf); return; }
  if(val==='tercero'){
    const nombre=(prompt('Nombre completo del tercero con carta poder:')||'').trim();
    if(!nombre){ sel.value=typeof S.poderes[uf]==='string'&&S.poderes[uf].startsWith('tercero:')?'tercero':''; return; }
    setPoder(u, 'tercero:'+nombre); save(); renderTop(); renderRow(uf);
  } else {
    setPoder(u, val); save(); renderTop(); renderRow(uf);
  }
});
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
    const act=Math.min(S.activa, st.mociones.length-1); S={presentes:st.presentes||{}, poderes:st.poderes||{}, mociones:st.mociones, activa:act, agenda:st.agenda||S.agenda||{}, palabra:st.palabra||S.palabra||[], respuestas:st.respuestas||S.respuestas||{}, objeciones:st.objeciones||S.objeciones||{}, cumplimiento:st.cumplimiento||S.cumplimiento||{presidentePropietario:null,dosFirmantes:null,antelacionOk:null}}; if(st.agenda===undefined) sync.legacy=true; save(); renderAll(); }
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
  ['agenda','preguntas','propos','docs','reglamento','normativa','encargado'].forEach(v=>$('#view-'+v).classList.toggle('vhide', t!==v));
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
  if(!C.preguntas || !C.preguntas.length){ $('#preguntasList').innerHTML = '<div class="card"><p class="note">Todavía no hay preguntas cargadas para esta asamblea. Las preguntas sobre la continuidad del encargado están en la pestaña <b>Encargado</b>.</p></div>'; return; }
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
  const vencida = Date.now()>DEADLINE.getTime();
  $('#proposList').innerHTML = S.mociones.map((m,i)=>{ const c=compute(m); const win=c.opts.filter(o=>!o.abst).sort((a,b)=>b.pct-a.pct)[0]; const objs=OBJ()[i]||{}; const oe=Object.keys(objs).map(k=>({uf:+k, ...objs[k]})).filter(o=>uf(o.uf)); const opoN=oe.length, opoPct=oe.reduce((s,o)=>s+uf(o.uf).pct,0);
    const votada = c.opts.reduce((s,o)=>s+o.n,0)>0;
    const ep = CTLogica.evaluarProposicion({n:opoN, pct:opoPct}, {N:N, totalPct:TOTAL_PCT}, vencida);
    const estadoLabel = !votada ? 'Sin votar todavía' : q.firm ? 'Decisión firme' : ep.estado==='decaida' ? 'Decaída (oposición alcanzó mayoría absoluta del total)' : ep.estado==='firme' ? 'Proposición firme (venció el plazo)' : 'Proposición en circulación';
    const pillClass = !votada ? 'pend' : q.firm ? 'tratado' : ep.estado==='decaida' ? '' : ep.estado==='firme' ? 'tratado' : 'curso';
    return `<div class="card prop"><h3>Moción ${i+1}: ${esc(m.titulo)}</h3><span class="pill ${pillClass}">${estadoLabel}</span>
      ${votada?`<div class="note">Resultado: ${c.opts.map(o=>`${esc(o.name)} ${fp(o.pct)} (${o.n} UF)`).join(' · ')}${win?` → mayoría: <b>${esc(win.name)}</b>`:''}</div>`:''}
      ${!q.firm&&votada?`<div class="stat"><div>Objeciones<b>${opoN}</b></div><div>Porcentual objetante<b>${fp(opoPct)}</b></div><div>Ausentes<b>${ausN} · ${fp(ausPct)}</b></div><div>Cierre<b style="font-size:15px">${DEADLINE.toLocaleDateString('es-AR')}</b></div></div>
      <div class="note">Oposición: ${opoN} UF / ${fp(opoPct)} — se necesita mayoría absoluta del total (${Math.floor(N/2)+1} UF y ${fp(TOTAL_PCT/2)}) para tumbarla</div>
      <div class="objlist">${oe.length?oe.map(o=>`<div class="obj"><b>${esc(uf(o.uf).piso)}</b><span>${esc(o.nombre||uf(o.uf).prop)}${o.motivo?` — <i>${esc(o.motivo)}</i>`:''}</span><span class="note">${new Date(o.ts).toLocaleDateString('es-AR')}</span></div>`).join(''):'<div class="note">Sin objeciones registradas.</div>'}</div>
      <div class="actions">${vencida?'':`<button class="btn primary sm" data-obj="${i}">Registrar objeción</button>`}</div>`:''}</div>`; }).join('') || '<div class="note">Todavía no hay mociones.</div>';
}
$('#view-propos').addEventListener('click', e=>{ const b=e.target.closest('button[data-obj]'); if(!b) return; const i=+b.dataset.obj; $('#objTitulo').textContent='Moción '+(i+1)+': '+S.mociones[i].titulo; ufOptions($('#objUf'), u=>!participa(u)); $('#objNombre').value=''; $('#objMotivo').value=''; $('#dlgObj').dataset.m=i; $('#dlgObj').showModal(); });
$('#objCancel').addEventListener('click', ()=>$('#dlgObj').close());
$('#objOk').addEventListener('click', ()=>{ const i=+$('#dlgObj').dataset.m; const u=+$('#objUf').value; if(!u){ toast('Elegí tu unidad'); return; } const nombre=$('#objNombre').value.trim(); if(!nombre){ toast('Escribí tu nombre'); return; } const motivo=$('#objMotivo').value.trim(); OBJ()[i]=OBJ()[i]||{}; OBJ()[i][u]={nombre, motivo, ts:Date.now()}; save(); sync.send({t:'objecion', m:i, uf:u, nombre, motivo}); $('#dlgObj').close(); renderAll(); toast('Objeción registrada'); });

// ---- reglamento / encargado — renderer con marked.js
// Pre-procesa encargado.md: envuelve la tabla Pandoc (grid-table) en un code fence
// para que marked la renderice como bloque monoespaciado en lugar de párrafos rotos.
function _preprocMd(md){
  // Detecta bloque de grid-table Pandoc: comienza con una línea de solo guiones/espacios
  // (al menos 20 guiones) y termina en la siguiente línea vacía tras la última fila.
  // Lo envuelve en ``` para que marked lo renderice como <pre><code>.
  return md.replace(/(^|\n)([ \t]*-{20,}[ \t\-]*\n[\s\S]*?-{20,}[ \t\-]*\n)(\n|$)/g,
    (_, pre, block, post) => pre + '```\n' + block + '```\n' + post);
}
function renderMarkdownEn(contenedorSel, indiceSel, md){
  const cont = $(contenedorSel);
  const indice = $(indiceSel);
  const prepared = _preprocMd(md || '');
  const html = marked.parse(prepared);
  cont.innerHTML = html;
  // Construir índice a partir de los headings ya renderizados
  const headings = cont.querySelectorAll('h2, h3');
  const nav = [];
  headings.forEach((el, i) => {
    const id = 'doc-' + i;
    el.id = id;
    const indent = el.tagName === 'H3' ? 'margin-left:1em;' : '';
    nav.push(`<a href="#${id}" style="${indent}" onclick="event.preventDefault();document.getElementById('${id}').scrollIntoView({behavior:'smooth',block:'start'})">${el.textContent}</a>`);
  });
  indice.innerHTML = nav.join('');
  // Reaplicar el filtro del buscador si ya hay algo escrito
  const buscarSel = contenedorSel === '#regTexto' ? '#regBuscar' : '#encBuscar';
  const q = ($( buscarSel)||{}).value||'';
  if(q) filtrarDoc(contenedorSel, q);
}
function filtrarDoc(contenedorSel, q){
  q = (q||'').trim().toLowerCase();
  for(const el of $(contenedorSel).querySelectorAll(':scope > p, :scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6, :scope > ul, :scope > ol, :scope > blockquote, :scope > pre, :scope > table, :scope > hr')){
    el.style.display = (!q || el.textContent.toLowerCase().includes(q)) ? '' : 'none';
  }
}
function renderReglamento(){
  renderMarkdownEn('#regTexto','#regIndiceNav', C.reglamento);
  filtrarDoc('#regTexto', ($('#regBuscar')||{}).value||'');
}
function filtrarReglamento(q){ filtrarDoc('#regTexto', q); }
// Cambia a la pestaña Reglamento y hace scroll al primer encabezado que incluya `texto`.
function irAReglamento(texto){ setTab('reglamento'); setTimeout(()=>{ const t=(texto||'').toLowerCase();
  for(const el of $('#regTexto').querySelectorAll('h2,h3,h4')){ if(el.textContent.toLowerCase().includes(t)){ el.scrollIntoView({behavior:'smooth',block:'start'}); break; } } }, 60); }
$('#regBuscar').addEventListener('input', e=>filtrarDoc('#regTexto', e.target.value));
function renderEncargado(){
  const md = (C.informe_admin||'') + '\n\n---\n\n' + (C.encargado||'');
  renderMarkdownEn('#encTexto','#encIndiceNav', md);
  filtrarDoc('#encTexto', ($('#encBuscar')||{}).value||'');
}
$('#encBuscar').addEventListener('input', e=>filtrarDoc('#encTexto', e.target.value));

// ---- normativa
function renderNormativa(){
  const items = C.normativa || [];
  $('#normativaList').innerHTML = items.map(n => {
    const textoHtml = n.texto
      ? `<details class="norm-texto-details"><summary>Ver texto completo del artículo</summary><div class="norm-texto-body">${n.texto.split('\n\n').map(p=>`<p>${esc(p)}</p>`).join('')}</div></details>`
      : '';
    return `
    <div class="card" id="norm-${esc(n.id)}">
      <h3>${esc(n.titulo)}</h3>
      <p>${esc(n.resumen)}</p>
      ${textoHtml}
      <p class="note">Fuente: ${esc(n.fuente)} — <a href="${esc(n.url)}" target="_blank" rel="noopener noreferrer">ver texto oficial</a></p>
    </div>`;
  }).join('');
}
function irANormativa(id){ setTab('normativa'); setTimeout(()=>{ const el=$('#norm-'+id); if(el) el.scrollIntoView({behavior:'smooth',block:'start'}); }, 60); }

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
renderAll = function(){ _renderAll(); if(TAB==='agenda') renderAgenda(); else if(TAB==='preguntas') renderPreguntas(); else if(TAB==='propos') renderPropos(); else if(TAB==='reglamento') renderReglamento(); else if(TAB==='normativa') renderNormativa(); else if(TAB==='encargado') renderEncargado(); };
(function(){ let t='agenda'; try{ t=localStorage.getItem(KEY+'-tab')||'agenda'; }catch(e){} setTab(t); })();

let tt; function toast(msg){ const t=$('#toast'); t.textContent=msg; t.style.display='block'; clearTimeout(tt); tt=setTimeout(()=>t.style.display='none',1800); }
renderAll();
})();
</script>
"""
out = HTML.replace("__DATA__", DATA).replace("__CONTENT__", CONTENT).replace("__LOGICA__", LOGICA).replace("__MARKED__", MARKED)
open(SC + "votacion-rivadavia-2069.html", "w", encoding="utf-8").write(out)
open(SC + "pages-out/index.html", "w", encoding="utf-8").write("<!doctype html>\n<html lang=\"es\">\n" + out + "\n</html>\n")
print("ok")
