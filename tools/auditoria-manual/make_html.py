import os
HERE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(HERE, "datos") + "/"
PRIVADO = os.environ.get("CT_PRIVADO", os.path.expanduser("~/consorcio-transparente-privado")) + "/"
import json
from collections import OrderedDict
from alerts import ALERTS, SEV_ORDER, BULLETS, DOC_FINDINGS

SC = DATOS
D = json.load(open(SC + "data.json"))
G, GJ, U, EV, EF, EFJ, CO, COJ, PA, PAJ, OB, SU = (D[k] for k in ("gastos","gastos_jul","units","evolucion","estado_fin","estado_fin_jul","composicion","composicion_jul","patrimonial","patrimonial_jul","obras","sueldos"))
TOT_A = round(sum(g["importe"] for g in G), 2); TOT_J = round(sum(g["importe"] for g in GJ), 2); TOT2 = round(TOT_A + TOT_J, 2)

cats = OrderedDict()
for g in G + GJ: cats.setdefault(g["categoria"], [0, 0])
for g in G: cats[g["categoria"]][0] += g["importe"]
for g in GJ: cats[g["categoria"]][1] += g["importe"]
categorias = [dict(rubro=k.title().replace("De ", "de ").replace("Y ", "y ").replace("En ", "en "), ago=round(a, 2), jul=round(j, 2)) for k, (a, j) in sorted(cats.items(), key=lambda x: -x[1][0])]

prov = OrderedDict()
for g in G + GJ: prov.setdefault(g["proveedor"], [0, 0])
for g in G: prov[g["proveedor"]][0] += g["importe"]
for g in GJ: prov[g["proveedor"]][1] += g["importe"]
proveedores = [dict(nombre=k, ago=round(a, 2), jul=round(j, 2)) for k, (a, j) in sorted(prov.items(), key=lambda x: -(x[1][0] + x[1][1]))]

agg = OrderedDict()
for o in OB:
    a = agg.setdefault(o["uf"], dict(uf=o["uf"], propietario=o["propietario"], n=0, total=0, jul=0, ago=0)); a["n"] += 1; a["total"] += o["total_obra"]; a["jul"] += o["pagado_jul"]; a["ago"] += o["pagado_ago"]
por_uf = sorted([dict(v, total=round(v["total"], 2), jul=round(v["jul"], 2), ago=round(v["ago"], 2), pagado=round(v["jul"] + v["ago"], 2)) for v in agg.values()], key=lambda x: -x["pagado"])

dj = {x["uf"]: x["deuda"] for x in D["deudores_jul"]}
deudores = sorted([dict(u, deuda_jul=dj.get(u["uf"])) for u in U if u["deuda"] > 0], key=lambda u: -u["deuda"])
deuda_total = round(sum(u["deuda"] for u in deudores), 2)

alerts = [dict(sev=s, area=a, titulo=t, evidencia=e, monto=m, rec=r) for s, a, t, e, m, r in sorted(ALERTS, key=lambda a: SEV_ORDER[a[0]])]
bullets = [dict(label=l, monto=m, det=d) for l, m, d in BULLETS]
evol = [dict(mes="Feb", a_cobrar=21134517.12, gastos=19521427.25, cobrado=18592951.79)] + [dict(mes=e["mes"][:3], a_cobrar=e["a_cobrar"], gastos=e["gastos"], cobrado=e["cobrado"]) for e in EV]

manifest = json.load(open(SC + "manifest.json"))
docstats = dict(total=sum(1 for m in manifest if m.get("archivo")), sin_adjunto=sum(1 for m in manifest if m["nombre"] == "(sin adjuntos)"), gastos=87)
docfind = [dict(mes=a, fecha=b, prov=c, imp=d, doc=e, hallazgo=f, sev=g) for a,b,c,d,e,f,g in sorted(DOC_FINDINGS, key=lambda x: SEV_ORDER[x[6]])]
payload = dict(docstats=docstats, docfind=docfind, totA=TOT_A, totJ=TOT_J, tot2=TOT2, ef=EF, efj=EFJ, co=CO, coj=COJ, pa=PA, paj=PAJ, categorias=categorias, proveedores=proveedores, porUf=por_uf, obras=OB,
               deudores=deudores, deudaTotal=deuda_total, deudaJul=4283350.11, alerts=alerts, bullets=bullets, evol=evol, units=U, sueldos=SU,
               efectivoJul=round(sum(g["importe"] for g in GJ if g["forma"].startswith("Efectivo")), 2), efectivoAgo=round(sum(g["importe"] for g in G if g["forma"].startswith("Efectivo")), 2))
DATA = json.dumps(payload, ensure_ascii=False)

HTML = r"""<meta charset="utf-8">
<title>Expensas Rivadavia 2069</title>
<meta name="description" content="Análisis de la liquidación de expensas de agosto 2026 del Consorcio Rivadavia 2069, contrastada con julio y verificada contra los comprobantes de Redconar.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --bg:#f2f3f5; --surface:#ffffff; --surface-2:#f7f8fa; --ink:#1b2536; --ink-2:#4c5563; --muted:#7a8391; --hair:#dfe2e8; --hair-2:#eceef2;
  --accent:#2a5db0; --accent-ink:#1f4a8f; --accent-soft:#e6eefb;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a;
  --critical:#d03b3b; --serious:#ec835a; --warning:#fab219; --info:#2a78d6; --good:#0ca30c;
  --critical-soft:#fbe4e4; --serious-soft:#fdeadf; --warning-soft:#fff3cf; --info-soft:#e3eefb;
  --shadow:0 1px 2px rgba(27,37,54,.06),0 8px 24px -12px rgba(27,37,54,.18);
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0f1318; --surface:#171c24; --surface-2:#1d232c; --ink:#eef1f5; --ink-2:#c3cad4; --muted:#8e98a6; --hair:#2a313c; --hair-2:#222932;
    --accent:#6f9ee8; --accent-ink:#9dbdf2; --accent-soft:#1c2a42;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70;
    --critical-soft:#3a1d1d; --serious-soft:#3b261a; --warning-soft:#3a3113; --info-soft:#1c2a42;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -12px rgba(0,0,0,.6);
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#0f1318; --surface:#171c24; --surface-2:#1d232c; --ink:#eef1f5; --ink-2:#c3cad4; --muted:#8e98a6; --hair:#2a313c; --hair-2:#222932;
  --accent:#6f9ee8; --accent-ink:#9dbdf2; --accent-soft:#1c2a42;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70;
  --critical-soft:#3a1d1d; --serious-soft:#3b261a; --warning-soft:#3a3113; --info-soft:#1c2a42;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -12px rgba(0,0,0,.6);
  color-scheme:dark;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
h1,h2,h3{font-family:"Source Serif 4",Georgia,"Times New Roman",serif;font-weight:600;letter-spacing:-.01em;text-wrap:balance;margin:0}
h1{font-size:clamp(28px,4vw,40px);line-height:1.1}
h2{font-size:24px;line-height:1.2}
h3{font-size:17px;line-height:1.3}
p{margin:0}
a{color:var(--accent-ink)}
.num{font-variant-numeric:tabular-nums}
.eyebrow{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.wrap{max-width:1140px;margin:0 auto;padding:0 24px}
@media (max-width:640px){.wrap{padding:0 14px}section{padding:30px 0 6px}h2{font-size:21px}.card{padding:14px 12px}.tile .val{font-size:21px}}
header.top{border-bottom:1px solid var(--hair);background:var(--surface)}
header.top .wrap{padding-top:36px;padding-bottom:28px;display:grid;gap:14px}
.lede{max-width:70ch;color:var(--ink-2);font-size:16px}
.meta{display:flex;flex-wrap:wrap;gap:8px 22px;font-size:13px;color:var(--muted)}
.meta b{color:var(--ink-2);font-weight:500}
nav.sticky{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--surface) 92%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--hair)}
nav.sticky .wrap{display:flex;gap:4px;overflow-x:auto;padding-top:6px;padding-bottom:6px;scrollbar-width:none}
nav.sticky a{white-space:nowrap;text-decoration:none;color:var(--ink-2);font-size:13px;font-weight:500;padding:6px 10px;border-radius:6px}
nav.sticky a:hover,nav.sticky a:focus-visible{background:var(--accent-soft);color:var(--accent-ink);outline:none}
section{padding:40px 0 8px}
section .wrap{display:grid;gap:18px}
.sec-head{display:grid;gap:6px;max-width:80ch}
.sec-head p{color:var(--ink-2)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--hair);border-radius:10px;padding:14px 16px;display:grid;gap:4px;align-content:start}
.tile .lab{font-size:12.5px;color:var(--muted);font-weight:500}
.tile .val{font-size:24px;font-weight:600;letter-spacing:-.01em;line-height:1.15}
.tile .sub{font-size:12.5px;color:var(--ink-2)}
.tile .delta{font-size:12.5px;font-weight:500}
.delta.up{color:var(--critical)} .delta.down{color:var(--good)} .delta.flat{color:var(--muted)}
.tile.warn{border-color:var(--critical);border-width:1px;box-shadow:inset 3px 0 0 var(--critical)}
.card{background:var(--surface);border:1px solid var(--hair);border-radius:10px;padding:18px 20px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:820px){.grid2{grid-template-columns:1fr}}
.bullets{display:grid;gap:0;background:var(--surface);border:1px solid var(--hair);border-radius:10px;overflow:hidden}
.bullet{display:grid;grid-template-columns:minmax(0,1fr) 150px;gap:6px 18px;padding:12px 18px;border-top:1px solid var(--hair-2);align-items:start}
.bullet:first-child{border-top:0}
.bullet .t{font-weight:600;grid-column:1;grid-row:1}
.bullet .d{font-size:13.5px;color:var(--ink-2);grid-column:1}
.bullet .m{text-align:right;font-weight:600;font-size:16px;grid-column:2;grid-row:1}
.bullet .bar{grid-column:2;height:6px;background:var(--hair-2);border-radius:3px;overflow:hidden}
.bullet .bar i{display:block;height:100%;background:var(--s1);border-radius:3px}
.bullet .pct{grid-column:2;text-align:right;font-size:12px;color:var(--muted)}
@media (max-width:640px){.bullet{grid-template-columns:1fr}.bullet .m,.bullet .bar,.bullet .pct{grid-column:1;text-align:left}.bullet .m{grid-row:auto}}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{border:1px solid var(--hair);background:var(--surface);color:var(--ink-2);border-radius:999px;padding:5px 12px;font-size:13px;font-weight:500;cursor:pointer;display:inline-flex;gap:6px;align-items:center}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--surface);border-color:var(--ink)}
.chip:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.alerts{display:grid;gap:10px}
.alert{background:var(--surface);border:1px solid var(--hair);border-radius:10px;overflow:hidden;box-shadow:none}
.alert summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:center;padding:13px 16px 13px 14px;border-left:4px solid var(--c)}
.alert summary::-webkit-details-marker{display:none}
.alert summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.alert .sev{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:3px 8px;border-radius:5px;background:var(--cs);color:var(--ink);white-space:nowrap}
.alert .ttl{font-weight:600;line-height:1.3}
.alert .area{font-size:12px;color:var(--muted);font-weight:500}
.alert .amt{font-weight:600;white-space:nowrap;color:var(--ink-2);font-size:14px}
.alert .body{padding:4px 16px 16px 18px;display:grid;gap:10px;border-left:4px solid var(--c);font-size:14px}
.alert .body b{font-weight:600;color:var(--ink)}
.alert .body p{color:var(--ink-2)}
.alert .rec{background:var(--surface-2);border-radius:8px;padding:10px 12px}
.alert[data-sev="CRÍTICO"]{--c:var(--critical);--cs:var(--critical-soft)}
.alert[data-sev="ALTO"]{--c:var(--serious);--cs:var(--serious-soft)}
.alert[data-sev="MEDIO"]{--c:var(--warning);--cs:var(--warning-soft)}
.alert[data-sev="BAJO"]{--c:var(--info);--cs:var(--info-soft)}
.alert .chev{width:10px;height:10px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(45deg);transition:transform .15s;margin-left:6px}
.alert[open] .chev{transform:rotate(-135deg)}
@media (max-width:640px){.alert summary{grid-template-columns:auto minmax(0,1fr)}.alert .amt{grid-column:2}}
.chart{width:100%;display:block;overflow:visible}
.chart text{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:12px;fill:var(--ink-2)}
@media (max-width:560px){.chart text{font-size:11px}}
.chart .axis text{fill:var(--muted);font-size:11px}
.chart .grid line{stroke:var(--hair-2)}
.chart .base{stroke:var(--hair)}
.chart .lbl{fill:var(--ink);font-weight:500}
.chart .val{fill:var(--ink-2);font-size:11.5px}
.chart .hit{fill:transparent;cursor:default}
.chart .hit:hover+rect,.chart .hit:hover+g rect{opacity:.85}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--ink-2);margin-bottom:6px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
.tip{position:fixed;z-index:20;pointer-events:none;background:var(--ink);color:var(--surface);font-size:12.5px;padding:8px 10px;border-radius:6px;box-shadow:var(--shadow);max-width:280px;line-height:1.4;display:none}
.tip b{font-weight:600;display:block}
.chart-title{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:8px}
.chart-title h3{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:14.5px;font-weight:600}
.chart-title span{font-size:12.5px;color:var(--muted)}
.tablewrap{overflow-x:auto;border:1px solid var(--hair);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th{position:sticky;top:0;background:var(--surface-2);text-align:left;font-weight:600;font-size:12px;letter-spacing:.02em;color:var(--ink-2);padding:9px 12px;border-bottom:1px solid var(--hair);white-space:nowrap}
td{padding:8px 12px;border-bottom:1px solid var(--hair-2);vertical-align:top}
tr:last-child td{border-bottom:0}
td.r,th.r{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.mut{color:var(--muted)}
tfoot td{font-weight:600;background:var(--surface-2)}
.pill{display:inline-block;font-size:11.5px;font-weight:500;padding:2px 8px;border-radius:999px;background:var(--surface-2);color:var(--ink-2);white-space:nowrap}
.pill.crit{background:var(--critical-soft)} .pill.ser{background:var(--serious-soft)} .pill.warn{background:var(--warning-soft)} .pill.ok{background:var(--info-soft)}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.toolbar input,.toolbar select{font:inherit;font-size:13.5px;padding:7px 10px;border:1px solid var(--hair);border-radius:7px;background:var(--surface);color:var(--ink)}
.toolbar input:focus-visible,.toolbar select:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.toolbar .count{font-size:13px;color:var(--muted)}
.fin{display:grid;grid-template-columns:1fr;gap:0}
.fin .row{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr) minmax(0,1fr);gap:10px;padding:7px 0;border-bottom:1px solid var(--hair-2);font-size:13.5px}
.fin .row.h{font-size:12px;color:var(--muted);font-weight:600;letter-spacing:.02em}
.fin .row.t{font-weight:600;border-bottom:0;border-top:1px solid var(--hair);padding-top:10px}
.fin .row .r{text-align:right}
.fin .neg{color:var(--critical)}
.note{font-size:13px;color:var(--muted);max-width:80ch}
.emp{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media (max-width:720px){.emp{grid-template-columns:1fr}}
.emp .card{display:grid;gap:8px}
.emp .kv{display:grid;grid-template-columns:1fr auto;gap:4px 12px;font-size:13.5px}
.emp .kv span:nth-child(2n){text-align:right}
.emp .kv .t{font-weight:600;border-top:1px solid var(--hair);padding-top:6px;margin-top:2px}
footer{padding:36px 0 48px;color:var(--muted);font-size:13px}
footer .wrap{display:grid;gap:8px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<header class="top">
  <div class="wrap">
    <div class="eyebrow">Consorcio de Propietarios Rivadavia 2069 · Balvanera, CABA · CUIT 33-60039145-9</div>
    <h1>Liquidación de expensas de agosto 2026, bajo la lupa</h1>
    <p class="lede">Análisis de gastos, cobranzas, deudores y flujo de fondos de la liquidación emitida el 31-08-2026 por Administración Almazare, contrastada con la de julio. Incluye los problemas detectados y qué pedirle a la administración.</p>
    <div class="meta"><span>Período <b>Agosto 2026</b></span><span>Vencimientos <b>10-09 (5%) · 20-09 (10%)</b></span><span>Unidades <b>94 departamentos · 1 local · 21 cocheras</b></span><span>Personal <b>2 empleados</b></span><span>Elaborado <b>03-09-2026</b></span></div>
  </div>
</header>
<nav class="sticky"><div class="wrap">
  <a href="#resumen">Resumen</a><a href="#plata">Dónde se fue la plata</a><a href="#problemas">Problemas</a><a href="#comprobantes">Comprobantes</a><a href="#flujo">Flujo de fondos</a><a href="#rubros">Rubros</a><a href="#proveedores">Proveedores</a><a href="#uf">Gasto por unidad</a><a href="#deudores">Deudores</a><a href="#evolucion">Evolución</a><a href="#cuentas">Estado de cuentas</a><a href="#sueldos">Sueldos</a>
</div></nav>

<section id="resumen"><div class="wrap">
  <div class="sec-head"><h2>Resumen del mes</h2><p>Los indicadores clave de agosto y su variación contra julio. Los tiles marcados en rojo son los que requieren acción.</p></div>
  <div class="tiles" id="tiles"></div>
</div></section>

<section id="plata"><div class="wrap">
  <div class="sec-head"><h2>Dónde se fue la plata</h2><p>Los destinos más grandes del gasto de julio y agosto sumados (<span class="num" id="tot2"></span>). La barra indica el peso de cada destino sobre ese total.</p></div>
  <div class="bullets" id="bullets"></div>
</div></section>

<section id="problemas"><div class="wrap">
  <div class="sec-head"><h2>Problemas detectados</h2><p>Ordenados por severidad. Cada uno muestra la evidencia tomada de las liquidaciones, el monto involucrado y qué pedir. Tocá un problema para ver el detalle.</p></div>
  <div class="chips" id="sevchips" role="group" aria-label="Filtrar por severidad"></div>
  <div class="alerts" id="alerts"></div>
</div></section>


<section id="comprobantes"><div class="wrap">
  <div class="sec-head"><h2>Lo que dicen los comprobantes</h2><p>Se descargaron y leyeron los <span id="docTotal"></span> adjuntos (facturas y comprobantes de pago) que la administración cargó en Redconar para las 87 líneas de gasto de julio y agosto. <span id="docSin"></span> líneas no tienen ningún respaldo. Los documentos están en la carpeta "Comprobantes Rivadavia 2069" de Descargas.</p></div>
  <div class="tiles" id="doctiles"></div>
  <div class="tablewrap"><table id="docfind"><thead><tr><th>Sev.</th><th>Fecha</th><th>Proveedor según liquidación</th><th class="r">Importe</th><th>Documento</th><th>Hallazgo</th></tr></thead><tbody></tbody></table></div>
</div></section>

<section id="flujo"><div class="wrap">
  <div class="sec-head"><h2>Flujo de fondos</h2><p>Cómo se movió la plata en cada mes: saldo inicial, lo que entró, lo que salió y cómo quedó repartido entre el banco y la caja en efectivo.</p></div>
  <div class="grid2">
    <div class="card"><div class="chart-title"><h3>Julio 2026</h3><span>de $12,0 M a $0,9 M</span></div><div id="wf-jul"></div></div>
    <div class="card"><div class="chart-title"><h3>Agosto 2026</h3><span>de $0,9 M a $1,9 M</span></div><div id="wf-ago"></div></div>
  </div>
  <div class="grid2">
    <div class="card"><div class="chart-title"><h3>Disponibilidades al cierre: banco vs. efectivo</h3><span>en pesos</span></div><div class="legend"><span><i style="background:var(--s1)"></i>Banco Galicia</span><span><i style="background:var(--s2)"></i>Caja (efectivo)</span></div><div id="bank"></div><p class="note">En agosto el 68% de la liquidez del consorcio está en efectivo en poder de la administración. En septiembre 2025 era el 66%.</p></div>
    <div class="card"><div class="chart-title"><h3>Estado financiero</h3><span>Ley 941 art. 10 inc. c</span></div><div class="fin" id="fin"></div></div>
  </div>
</div></section>

<section id="rubros"><div class="wrap">
  <div class="sec-head"><h2>Gastos por rubro</h2><p>Agosto sumó <span class="num" id="totA"></span> y julio <span class="num" id="totJ"></span>. Las dos categorías "Servicios públicos" del PDF están unificadas.</p></div>
  <div class="card"><div class="legend"><span><i style="background:var(--s1)"></i>Agosto 2026</span><span><i style="background:var(--s2)"></i>Julio 2026</span></div><div id="cats"></div></div>
</div></section>

<section id="proveedores"><div class="wrap">
  <div class="sec-head"><h2>Quiénes se llevan la plata</h2><p>Los 14 proveedores con mayor cobro en julio y agosto. Entre los siete primeros se llevan dos de cada tres pesos gastados.</p></div>
  <div class="card"><div class="legend"><span><i style="background:var(--s1)"></i>Agosto 2026</span><span><i style="background:var(--s2)"></i>Julio 2026</span></div><div id="provs"></div></div>
  <div class="tablewrap"><table id="provtable"><thead><tr><th>#</th><th>Proveedor</th><th class="r">Agosto</th><th class="r">Julio</th><th class="r">Total 2 meses</th><th class="r">% del gasto</th><th class="r">% acumulado</th></tr></thead><tbody></tbody></table></div>
</div></section>

<section id="uf"><div class="wrap">
  <div class="sec-head"><h2>Gasto aplicado a unidades funcionales</h2><p>Obras y gastos que beneficiaron a unidades concretas, no a las partes comunes en general. En dos meses el consorcio pagó <span class="num" id="ufPagado"></span> por este concepto y quedan <span class="num" id="ufPend"></span> comprometidos.</p></div>
  <div class="card"><div class="legend"><span><i style="background:var(--s1)"></i>Pagado en agosto</span><span><i style="background:var(--s2)"></i>Pagado en julio</span></div><div id="ufchart"></div></div>
  <div class="tablewrap"><table id="obras"><thead><tr><th>Unidad beneficiaria</th><th>Propietario</th><th>Obra / concepto</th><th>Proveedor</th><th class="r">Costo total</th><th class="r">Pagado jul + ago</th><th class="r">Pendiente</th><th>Observación</th></tr></thead><tbody></tbody></table></div>
</div></section>

<section id="deudores"><div class="wrap">
  <div class="sec-head"><h2>Deudores</h2><p>Nueve unidades con saldo deudor por <span class="num" id="deudaTot"></span> (julio: $4.283.350). Tres unidades concentran el 72% de la deuda. Cuatro no pagaron nada en agosto.</p></div>
  <div class="card"><div class="chart-title"><h3>Deuda por unidad y meses de expensa que representa</h3><span>agosto 2026</span></div><div id="debt"></div></div>
  <div class="tablewrap"><table id="debttable"><thead><tr><th>UF</th><th>Unidad</th><th>Propietario</th><th class="r">Deuda agosto</th><th class="r">Deuda julio</th><th class="r">Pagó en agosto</th><th class="r">Interés</th><th class="r">Tasa</th><th class="r">Meses</th><th>Estado</th></tr></thead><tbody></tbody></table></div>
  <p class="note">Tasa = interés del mes sobre la deuda. Va del 7,2% (UC-1, el mayor deudor) al 25,6% (5-A): no hay un criterio uniforme. La UF 27 no es mora, es un llavero debitado al propietario.</p>
</div></section>

<section id="evolucion"><div class="wrap">
  <div class="sec-head"><h2>Evolución febrero a agosto 2026</h2><p>Lo prorrateado a los propietarios, lo gastado y lo efectivamente cobrado cada mes. En siete meses se prorrateó $172 M, se gastó $162 M y se cobró $160 M.</p></div>
  <div class="card"><div class="legend"><span><i style="background:var(--s1)"></i>Importe a cobrar (prorrateado)</span><span><i style="background:var(--s2)"></i>Gastos del mes</span><span><i style="background:var(--s3)"></i>Expensas cobradas</span></div><div id="evol"></div></div>
</div></section>

<section id="cuentas"><div class="wrap">
  <div class="sec-head"><h2>Estado de cuentas por unidad</h2><p>Las 116 unidades con su saldo anterior, pagos, deuda, interés, expensa del mes y total a pagar. Buscá por propietario o unidad, o filtrá por estado.</p></div>
  <div class="toolbar"><input id="q" type="search" placeholder="Buscar propietario o unidad…" aria-label="Buscar"><select id="st" aria-label="Filtrar por estado"><option value="">Todos los estados</option></select><span class="count" id="cnt"></span></div>
  <div class="tablewrap" style="max-height:560px;overflow:auto"><table id="units"><thead><tr><th>UF</th><th>Unidad</th><th>Propietario</th><th class="r">Saldo ant.</th><th class="r">Pagos</th><th class="r">Deuda</th><th class="r">Interés</th><th class="r">% A</th><th class="r">Expensa mes</th><th class="r">A pagar</th><th>Estado</th></tr></thead><tbody></tbody><tfoot></tfoot></table></div>
</div></section>

<section id="sueldos"><div class="wrap">
  <div class="sec-head"><h2>Sueldos y cargas sociales</h2><p>Período julio 2026, pagado en agosto. El rubro sumó $5,95 M en agosto y $9,34 M en julio (con aguinaldo).</p></div>
  <div class="emp" id="emp"></div>
  <p class="note">Ambos recibos incluyen un "Adicional" de $55.000 sin concepto. El encargado cobra 23 horas extra al 50% ($318.838, 14% de su bruto). Las cargas patronales (F.931) se pagan sistemáticamente un mes después de su vencimiento.</p>
</div></section>

<footer><div class="wrap">
  <p><b>Método y verificaciones.</b> Se transcribieron las 43 líneas de gasto de agosto y las 44 de julio y las 116 filas del estado de cuentas. Todos los totales cuadran al centavo con el PDF: gastos por columna y rubro, estado financiero, composición banco/caja, prorrateo (A, B, D), deuda, intereses y total a pagar. La referencia interanual proviene de la liquidación de septiembre 2025. Los 150 comprobantes se descargaron del portal de propietarios de Redconar el 03-09-2026 y se leyeron uno por uno; los hallazgos citan el documento exacto.</p>
  <p>Los problemas señalados son hallazgos documentales que requieren aclaración de la administración; no constituyen una imputación. El Excel adjunto contiene el detalle completo y los anexos.</p>
</div></footer>
<div class="tip" id="tip" role="tooltip"></div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
const D = JSON.parse(document.getElementById('data').textContent);
const fmt = new Intl.NumberFormat('es-AR',{style:'currency',currency:'ARS',maximumFractionDigits:0});
const fmtM = v => { const a=Math.abs(v); const s=v<0?'-':''; return a>=1e6 ? s+'$'+(a/1e6).toFixed(a>=1e7?1:2).replace('.',',')+' M' : a>=1e3 ? s+'$'+Math.round(a/1e3)+' mil' : s+'$'+Math.round(a); };
const pct = (v,d=1) => (v*100).toFixed(d).replace('.',',')+'%';
const $ = s => document.querySelector(s);
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const tip = $('#tip');
function showTip(e, html){ tip.innerHTML = html; tip.style.display='block'; moveTip(e); }
function moveTip(e){ const w=tip.offsetWidth, h=tip.offsetHeight; let x=e.clientX+14, y=e.clientY+14; if(x+w>innerWidth-8) x=e.clientX-w-14; if(y+h>innerHeight-8) y=e.clientY-h-14; tip.style.left=x+'px'; tip.style.top=y+'px'; }
function hideTip(){ tip.style.display='none'; }
function bindTip(el, html){ el.addEventListener('mouseenter', e=>showTip(e,html)); el.addEventListener('mousemove', moveTip); el.addEventListener('mouseleave', hideTip); }
const NS='http://www.w3.org/2000/svg';
function el(n, attrs, parent){ const e=document.createElementNS(NS,n); for(const k in attrs) e.setAttribute(k, attrs[k]); if(parent) parent.appendChild(e); return e; }
function esc(s){ return String(s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

// ---------- tiles
const ef=D.ef, efj=D.efj, pa=D.pa, paj=D.paj;
const cajaShare = D.co[1].saldo_cierre/ef.saldo_cierre;
const tiles = [
 {lab:'Gastos del mes', val:D.totA, prev:D.totJ, sub:'Julio incluyó aguinaldo y un anticipo de obra de $5 M'},
 {lab:'Expensas cobradas', val:ef.ing_termino+ef.ing_adeudadas+ef.ing_intereses+ef.ing_adelantadas, prev:efj.ing_termino+efj.ing_adeudadas+efj.ing_intereses+efj.ing_adelantadas, sub:'89,8% del saldo anterior de los propietarios'},
 {lab:'Prorrateado a cobrar', val:31705960.60, prev:31122626.83, sub:'$1,83 M por encima del gasto, sin concepto'},
 {lab:'Disponibilidades al cierre', val:ef.saldo_cierre, prev:efj.saldo_cierre, sub:pct(cajaShare,0)+' en efectivo en poder de la administración', warn:true, invert:true},
 {lab:'Facturas pendientes de pago', val:-pa.facturas_pend, prev:-paj.facturas_pend, sub:'Cubiertas solo al '+pct(ef.saldo_cierre/(-pa.facturas_pend),0)+' por las disponibilidades', warn:true},
 {lab:'Deuda de propietarios', val:D.deudaTotal, prev:D.deudaJul, sub:'9 unidades · UC-1 concentra el 35%', warn:true},
 {lab:'Obras en unidades privadas', val:7585333.33+2650000, prev:10203457.01+2650000, sub:'Liquidadas como expensas ordinarias', warn:true},
 {lab:'Pagado en efectivo a proveedores', val:D.efectivoAgo, prev:D.efectivoJul, sub:'Julio: seguridad $2,7 M, porcelanato $2 M + $2 M', warn:true},
];
$('#tiles').innerHTML = tiles.map(t=>{
  const d = t.prev ? (t.val/t.prev-1) : null;
  let cls='flat', txt='sin dato julio';
  if(d!==null){ const worse = t.invert ? d<0 : d>0; cls = Math.abs(d)<0.005?'flat':(worse?'up':'down'); txt=(d>0?'+':'')+pct(d)+' vs. julio'; }
  return `<div class="tile${t.warn?' warn':''}"><div class="lab">${t.lab}</div><div class="val num">${fmt.format(t.val)}</div><div class="delta ${cls}">${txt}</div><div class="sub">${t.sub}</div></div>`;
}).join('');

// ---------- bullets
$('#tot2').textContent = fmt.format(D.tot2);
$('#bullets').innerHTML = D.bullets.map(b=>`<div class="bullet"><div class="t">${esc(b.label)}</div><div class="m num">${fmt.format(b.monto)}</div><div class="d">${esc(b.det)}</div><div class="bar"><i style="width:${(b.monto/D.tot2*100).toFixed(1)}%"></i></div><div class="pct num">${pct(b.monto/D.tot2)} del gasto de 2 meses</div></div>`).join('');

// ---------- alerts
const sevs=['CRÍTICO','ALTO','MEDIO','BAJO']; const sevCol={ 'CRÍTICO':'--critical','ALTO':'--serious','MEDIO':'--warning','BAJO':'--info'};
let sevFilter = null;
function renderAlerts(){
  $('#alerts').innerHTML = D.alerts.filter(a=>!sevFilter||a.sev===sevFilter).map((a,i)=>`<details class="alert" data-sev="${a.sev}"${a.sev==='CRÍTICO'?' open':''}>
   <summary><span class="sev">${a.sev}</span><span><div class="ttl">${esc(a.titulo)}</div><div class="area">${esc(a.area)}</div></span><span style="display:flex;align-items:center;gap:8px"><span class="amt num">${a.monto?fmt.format(a.monto):''}</span><i class="chev"></i></span></summary>
   <div class="body"><p><b>Evidencia.</b> ${esc(a.evidencia)}</p><div class="rec"><b>Qué pedir.</b> ${esc(a.rec)}</div></div></details>`).join('');
}
$('#sevchips').innerHTML = `<button class="chip" aria-pressed="true" data-sev="">Todos (${D.alerts.length})</button>` + sevs.map(s=>`<button class="chip" aria-pressed="false" data-sev="${s}"><span class="dot" style="background:var(${sevCol[s]})"></span>${s.charAt(0)+s.slice(1).toLowerCase()} (${D.alerts.filter(a=>a.sev===s).length})</button>`).join('');
$('#sevchips').addEventListener('click', e=>{ const b=e.target.closest('.chip'); if(!b) return; sevFilter=b.dataset.sev||null; [...$('#sevchips').children].forEach(c=>c.setAttribute('aria-pressed', c===b)); renderAlerts(); });
renderAlerts();


// ---------- comprobantes
$('#docTotal').textContent = D.docstats.total; $('#docSin').textContent = D.docstats.sin_adjunto;
const toAcosta = 2000000+2552000+205392;
$('#doctiles').innerHTML = [
 {lab:'Pagos que fueron a la propietaria de 13-B', val:toAcosta, sub:'Recibo en efectivo firmado por ella + 2 transferencias a su cuenta, registrados como Saczewiczyk y LEV Rental', warn:true},
 {lab:'Efectivo con recibo manuscrito', val:2696045.29, sub:'Seguridad C.S.I., julio: recibo de librería firmado "Pamela Ogando"', warn:true},
 {lab:'Transferido por error al abogado', val:1350000, sub:'Por una factura de $135.000; devolvió $1.215.000 al día siguiente', warn:true},
 {lab:'Factura personal del encargado pagada como haberes', val:159406.40, sub:'Flow Full + Deco + línea móvil a nombre de Ramón Gonzalez, julio y agosto', warn:true},
 {lab:'Pagado a un tercero distinto del emisor', val:350000, sub:'Mathil → Soluciones en Extinguidores; Lopez Ramirez → Lopez Mareco'},
 {lab:'Líneas de gasto sin ningún adjunto', val:D.docstats.sin_adjunto, sub:'Allianz, Berkley, Galicia, honorarios admin julio, FATERYH julio', count:true},
].map(t=>`<div class="tile${t.warn?' warn':''}"><div class="lab">${t.lab}</div><div class="val num">${t.count?t.val:fmt.format(t.val)}</div><div class="sub">${t.sub}</div></div>`).join('');
const sevPill = s=>({'CRÍTICO':'crit','ALTO':'ser','MEDIO':'warn','BAJO':'ok'}[s]||'');
$('#docfind tbody').innerHTML = D.docfind.map(f=>`<tr><td><span class="pill ${sevPill(f.sev)}">${f.sev}</span></td><td class="mut" style="white-space:nowrap">${f.fecha||f.mes}</td><td>${esc(f.prov)}</td><td class="r">${fmt.format(f.imp)}</td><td class="mut">${esc(f.doc)}</td><td>${esc(f.hallazgo)}</td></tr>`).join('');

// ---------- generic horizontal bar chart (stacked series)
function hbars(container, rows, series, opts){
  opts = Object.assign({labelW:210, rowH:26, gap:8, valueFmt:fmtM, right:110, W:900}, opts||{});
  const cw = container.clientWidth||900; const narrow = cw < 560;
  if(narrow){ opts.labelW = Math.min(opts.labelW, 132); opts.right = 74; opts.rowH = Math.max(22, opts.rowH-2); }
  const W = Math.max(320, Math.min(opts.W, cw)), H = rows.length*(opts.rowH+opts.gap)+8;
  const svg = el('svg',{class:'chart',viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':opts.aria||''});
  const max = Math.max(...rows.map(r=>series.reduce((s,k)=>s+(r[k.key]||0),0)));
  const x0 = opts.labelW, x1 = W-opts.right, sx = v=>x0+(v/max)*(x1-x0);
  const g = el('g',{class:'grid'},svg);
  const ticks = niceTicks(0,max,narrow?2:4);
  ticks.forEach(t=>{ el('line',{x1:sx(t),x2:sx(t),y1:0,y2:H-8,class:t===0?'base':''},g); const tx=el('text',{x:sx(t),y:H-1,'text-anchor':'middle',class:'axis'},svg); tx.textContent=fmtM(t); tx.setAttribute('class','axis'); });
  rows.forEach((r,i)=>{
    const y = i*(opts.rowH+opts.gap);
    const lab = el('text',{x:x0-10,y:y+opts.rowH/2+4,'text-anchor':'end',class:'lbl'},svg); const maxc = narrow ? 19 : 30; lab.textContent = r.label.length>maxc? r.label.slice(0,maxc-1)+'…' : r.label;
    let acc=0; const total = series.reduce((s,k)=>s+(r[k.key]||0),0);
    const grp = el('g',{},svg);
    series.forEach((s,si)=>{
      const v=r[s.key]||0; if(v<=0) return;
      const bx=sx(acc), bw=Math.max(0,sx(acc+v)-sx(acc)-(si<series.length-1&&v>0?2:0));
      const rect = el('rect',{x:bx,y:y+2,width:bw,height:opts.rowH-4,fill:`var(${s.color})`,rx:(si===series.length-1||acc+v>=total-0.01)?3:0},grp);
      bindTip(rect, `<b>${esc(r.label)}</b>${esc(s.name)}: ${fmt.format(v)}${series.length>1?`<br>Total: ${fmt.format(total)}`:''}${r.extra?'<br>'+esc(r.extra):''}`);
      acc+=v;
    });
    const vt = el('text',{x:sx(total)+6,y:y+opts.rowH/2+4,class:'val'},svg); vt.textContent = opts.valueFmt(total) + (r.suffix&&!narrow?('  '+r.suffix):'');
  });
  container.innerHTML=''; container.appendChild(svg);
}
function niceTicks(min,max,n){ const span=max-min, step0=span/n, mag=Math.pow(10,Math.floor(Math.log10(step0))); const step=[1,2,2.5,5,10].map(m=>m*mag).find(s=>span/s<=n)||mag*10; const out=[]; for(let v=0; v<=max+1e-9; v+=step) out.push(v); return out; }

// ---------- waterfall
function waterfall(container, steps, aria){
  const W=Math.max(300, Math.min(520, container.clientWidth||440)), H=230, padL=8, padR=8, top=28, bottom=40;
  const svg = el('svg',{class:'chart',viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':aria});
  let run=0; const bars=[];
  steps.forEach(s=>{ if(s.kind==='total'){ bars.push({label:s.label, y0:0, y1:s.value, kind:'total'}); run=s.value; } else { bars.push({label:s.label, y0:run, y1:run+s.value, kind:s.value>=0?'in':'out'}); run+=s.value; } });
  const max = Math.max(...bars.map(b=>Math.max(b.y0,b.y1)));
  const sy = v => top + (1-v/max)*(H-top-bottom);
  const bw = (W-padL-padR)/bars.length, barW = bw*0.62;
  const grid = el('g',{class:'grid'},svg); niceTicks(0,max,4).forEach(t=>{ el('line',{x1:padL,x2:W-padR,y1:sy(t),y2:sy(t),class:t===0?'base':''},grid); });
  bars.forEach((b,i)=>{
    const x=padL+i*bw+(bw-barW)/2, yA=sy(Math.max(b.y0,b.y1)), yB=sy(Math.min(b.y0,b.y1));
    const color = b.kind==='total'?'--s1':(b.kind==='in'?'--s3':'--s2');
    const rect = el('rect',{x:x,y:yA,width:barW,height:Math.max(2,yB-yA),fill:`var(${color})`,rx:3},svg);
    bindTip(rect, `<b>${esc(b.label)}</b>${fmt.format(b.y1-b.y0)}${b.kind!=='total'?`<br>Acumulado: ${fmt.format(b.y1)}`:''}`);
    if(i<bars.length-1) el('line',{x1:x+barW,x2:x+barW+(bw-barW),y1:sy(b.y1),y2:sy(b.y1),stroke:'var(--hair)','stroke-dasharray':'3 3'},svg);
    const vt=el('text',{x:x+barW/2,y:yA-6,'text-anchor':'middle',class:'val'},svg); vt.textContent=(b.kind==='out'?'−':'')+fmtM(Math.abs(b.y1-b.y0));
    const lt=el('text',{x:x+barW/2,y:H-bottom+16,'text-anchor':'middle',class:'axis'},svg); lt.textContent=b.label;
    if(b.sub){ const st=el('text',{x:x+barW/2,y:H-bottom+30,'text-anchor':'middle',class:'axis'},svg); st.textContent=b.sub; }
  });
  container.innerHTML=''; container.appendChild(svg);
}
function drawAll(){
waterfall($('#wf-jul'), [{label:'Saldo inicial',value:efj.saldo_anterior,kind:'total'},{label:'Cobrado',value:efj.ing_termino+efj.ing_adeudadas+efj.ing_intereses+efj.ing_adelantadas},{label:'Gastos',value:-efj.egresos},{label:'Saldo final',value:efj.saldo_cierre,kind:'total'}], 'Flujo de fondos de julio');
waterfall($('#wf-ago'), [{label:'Saldo inicial',value:ef.saldo_anterior,kind:'total'},{label:'Cobrado',value:ef.ing_termino+ef.ing_adeudadas+ef.ing_intereses+ef.ing_adelantadas},{label:'Gastos',value:-ef.egresos},{label:'Saldo final',value:ef.saldo_cierre,kind:'total'}], 'Flujo de fondos de agosto');

hbars($('#bank'), [
  {label:'Junio 2026', banco:D.coj[0].saldo_ant, caja:D.coj[1].saldo_ant},
  {label:'Julio 2026', banco:D.coj[0].saldo_cierre, caja:D.coj[1].saldo_cierre, extra:'Caja: '+pct(D.coj[1].saldo_cierre/efj.saldo_cierre,0)},
  {label:'Agosto 2026', banco:D.co[0].saldo_cierre, caja:D.co[1].saldo_cierre, extra:'Caja: '+pct(cajaShare,0)},
], [{key:'banco',name:'Banco Galicia',color:'--s1'},{key:'caja',name:'Caja (efectivo)',color:'--s2'}], {W:460, labelW:95, right:70, rowH:30, gap:10, aria:'Disponibilidades banco vs caja'});

// ---------- estado financiero
const finRows = [['Saldo anterior','saldo_anterior'],['Ingresos por expensas en término','ing_termino'],['Ingresos por expensas adeudadas','ing_adeudadas'],['Ingresos por intereses','ing_intereses'],['Ingresos por expensas adelantadas','ing_adelantadas'],['Egresos por gastos del mes','egresos'],['Saldo al cierre','saldo_cierre']];
$('#fin').innerHTML = `<div class="row h"><span>Concepto</span><span class="r">Agosto</span><span class="r">Julio</span></div>` + finRows.map(([l,k])=>{ const neg=k==='egresos'; return `<div class="row${k==='saldo_cierre'?' t':''}"><span>${l}</span><span class="r num${neg?' neg':''}">${neg?'−':''}${fmt.format(ef[k])}</span><span class="r num${neg?' neg':''}">${neg?'−':''}${fmt.format(efj[k])}</span></div>`; }).join('')
 + `<div class="row"><span style="color:var(--muted)">Facturas pendientes de pago</span><span class="r num neg">−${fmt.format(-pa.facturas_pend)}</span><span class="r num neg">−${fmt.format(-paj.facturas_pend)}</span></div><div class="row t"><span>Disponibilidades menos pendientes</span><span class="r num neg">${fmt.format(ef.saldo_cierre+pa.facturas_pend)}</span><span class="r num neg">${fmt.format(efj.saldo_cierre+paj.facturas_pend)}</span></div>`;

// ---------- categorías (grouped as two stacked rows? -> use grouped: draw two thin bars per row)
function grouped(container, rows, series, opts){
  opts = Object.assign({labelW:230, barH:11, gap:10, right:110}, opts||{});
  const cw = container.clientWidth||900; const narrow = cw < 560;
  if(narrow){ opts.labelW = 132; opts.right = 66; }
  const rowH = series.length*opts.barH+series.length-1;
  const W=Math.max(320, Math.min(900, cw)), H=rows.length*(rowH+opts.gap)+8, x0=opts.labelW, x1=W-opts.right;
  const max=Math.max(...rows.flatMap(r=>series.map(s=>r[s.key]||0)));
  const sx=v=>x0+(v/max)*(x1-x0);
  const svg=el('svg',{class:'chart',viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':opts.aria||''});
  const g=el('g',{class:'grid'},svg); niceTicks(0,max,narrow?2:4).forEach(t=>{ el('line',{x1:sx(t),x2:sx(t),y1:0,y2:H-8,class:t===0?'base':''},g); const tx=el('text',{x:sx(t),y:H-1,'text-anchor':'middle',class:'axis'},svg); tx.textContent=fmtM(t); });
  rows.forEach((r,i)=>{ const y=i*(rowH+opts.gap);
    const lab=el('text',{x:x0-10,y:y+rowH/2+4,'text-anchor':'end',class:'lbl'},svg); lab.textContent=narrow&&r.label.length>19?r.label.slice(0,18)+'…':r.label;
    series.forEach((s,si)=>{ const v=r[s.key]||0; const by=y+si*(opts.barH+1);
      const rect=el('rect',{x:sx(0),y:by,width:Math.max(0,sx(v)-sx(0)),height:opts.barH,fill:`var(${s.color})`,rx:2},svg);
      bindTip(rect,`<b>${esc(r.label)}</b>${s.name}: ${fmt.format(v)}${r.pct?'<br>'+r.pct[si]:''}`);
      if(si===0){ const vt=el('text',{x:sx(v)+6,y:by+opts.barH-1,class:'val'},svg); vt.textContent=fmtM(v)+(r.delta!=null&&!narrow?`  (${r.delta>0?'+':''}${pct(r.delta,0)})`:''); }
    });
  });
  container.innerHTML=''; container.appendChild(svg);
}
grouped($('#cats'), D.categorias.map(c=>({label:c.rubro, ago:c.ago, jul:c.jul, delta:c.jul?c.ago/c.jul-1:null, pct:[pct(c.ago/D.totA)+' de agosto', pct(c.jul/D.totJ)+' de julio']})), [{key:'ago',name:'Agosto',color:'--s1'},{key:'jul',name:'Julio',color:'--s2'}], {aria:'Gastos por rubro agosto vs julio'});
$('#totA').textContent=fmt.format(D.totA); $('#totJ').textContent=fmt.format(D.totJ);

// ---------- proveedores
const top = D.proveedores.slice(0,14);
hbars($('#provs'), top.map(p=>({label:p.nombre.replace('Consorcio Rivadavia 2069 (sueldos)','Sueldos (2 empleados)').replace('MAGNUM FUMIGACIONES (Escuchuri)','MAGNUM FUMIGACIONES'), ago:p.ago, jul:p.jul, extra:pct((p.ago+p.jul)/D.tot2)+' del gasto de 2 meses'})), [{key:'ago',name:'Agosto',color:'--s1'},{key:'jul',name:'Julio',color:'--s2'}], {labelW:230, rowH:22, gap:7, aria:'Proveedores por monto cobrado'});
let acc=0; $('#provtable tbody').innerHTML = D.proveedores.map((p,i)=>{ const t=p.ago+p.jul; acc+=t; return `<tr><td class="mut">${i+1}</td><td>${esc(p.nombre)}</td><td class="r">${fmt.format(p.ago)}</td><td class="r">${fmt.format(p.jul)}</td><td class="r"><b>${fmt.format(t)}</b></td><td class="r">${pct(t/D.tot2)}</td><td class="r mut">${pct(acc/D.tot2)}</td></tr>`; }).join('');

// ---------- gasto por UF
const ufRows = D.porUf.filter(u=>u.pagado>0);
hbars($('#ufchart'), ufRows.map(u=>({label:u.uf, ago:u.ago, jul:u.jul, extra:`${u.propietario} · costo total ${fmt.format(u.total)} · pendiente ${fmt.format(u.total-u.pagado)}`})), [{key:'ago',name:'Pagado en agosto',color:'--s1'},{key:'jul',name:'Pagado en julio',color:'--s2'}], {labelW:260, rowH:24, gap:8, aria:'Gasto pagado por unidad beneficiaria'});
const ufPag = D.obras.reduce((s,o)=>s+o.pagado_2m,0), ufPend = D.obras.reduce((s,o)=>s+o.pendiente,0);
$('#ufPagado').textContent=fmt.format(ufPag); $('#ufPend').textContent=fmt.format(ufPend);
$('#obras tbody').innerHTML = D.obras.map(o=>`<tr><td><b>${esc(o.uf)}</b></td><td>${esc(o.propietario)}</td><td>${esc(o.obra)}</td><td>${esc(o.proveedor)}</td><td class="r">${fmt.format(o.total_obra)}</td><td class="r">${fmt.format(o.pagado_2m)}</td><td class="r">${o.pendiente>0.5?fmt.format(o.pendiente):'—'}</td><td class="mut">${esc(o.obs||'')}</td></tr>`).join('')
 + `<tr><td colspan="4"><b>Total</b></td><td class="r"><b>${fmt.format(D.obras.reduce((s,o)=>s+o.total_obra,0))}</b></td><td class="r"><b>${fmt.format(ufPag)}</b></td><td class="r"><b>${fmt.format(ufPend)}</b></td><td></td></tr>`;

// ---------- deudores
$('#deudaTot').textContent = fmt.format(D.deudaTotal);
const dd = D.deudores.filter(u=>u.uf!==27);
hbars($('#debt'), dd.map(u=>({label:`${u.piso_depto} · ${u.propietario}`, deuda:u.deuda, suffix:u.meses_deuda.toFixed(1).replace('.',',')+' meses', extra:`${u.pagos>0?'Pagó '+fmt.format(u.pagos)+' en agosto':'No pagó nada en agosto'} · interés ${fmt.format(u.interes)} (${pct(u.tasa_int_sobre_deuda||0)})`})), [{key:'deuda',name:'Deuda',color:'--s2'}], {labelW:230, rowH:24, gap:8, right:150, aria:'Deuda por unidad'});
$('#debttable tbody').innerHTML = D.deudores.map(u=>`<tr><td class="mut">${u.uf}</td><td>${u.piso_depto}</td><td>${esc(u.propietario)}</td><td class="r"><b>${fmt.format(u.deuda)}</b></td><td class="r">${u.deuda_jul!=null?fmt.format(u.deuda_jul):'<span class="mut">nuevo</span>'}</td><td class="r">${u.pagos>0?fmt.format(u.pagos):'<span class="pill crit">sin pago</span>'}</td><td class="r">${fmt.format(u.interes)}</td><td class="r">${u.tasa_int_sobre_deuda?pct(u.tasa_int_sobre_deuda):'—'}</td><td class="r">${u.meses_deuda.toFixed(1).replace('.',',')}</td><td>${esc(u.estado)}</td></tr>`).join('')
 + `<tr><td colspan="3"><b>Total</b></td><td class="r"><b>${fmt.format(D.deudaTotal)}</b></td><td class="r"><b>${fmt.format(D.deudaJul)}</b></td><td class="r">${fmt.format(D.deudores.reduce((s,u)=>s+u.pagos,0))}</td><td class="r"><b>${fmt.format(D.deudores.reduce((s,u)=>s+u.interes,0))}</b></td><td></td><td></td><td></td></tr>`;

// ---------- evolución (line chart, one scale)
(function(){
  const cw=$('#evol').clientWidth||900, narrow=cw<560; const W=Math.max(320,Math.min(900,cw)),H=narrow?260:300,padL=narrow?52:70,padR=narrow?50:20,top=20,bottom=40; const rows=D.evol;
  const series=[{key:'a_cobrar',name:'Importe a cobrar',color:'--s1'},{key:'gastos',name:'Gastos del mes',color:'--s2'},{key:'cobrado',name:'Expensas cobradas',color:'--s3'}];
  const max=Math.max(...rows.flatMap(r=>series.map(s=>r[s.key])))*1.08;
  const sx=i=>padL+i*(W-padL-padR)/(rows.length-1), sy=v=>top+(1-v/max)*(H-top-bottom);
  const svg=el('svg',{class:'chart',viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':'Evolución mensual'});
  const g=el('g',{class:'grid'},svg); niceTicks(0,max,5).forEach(t=>{ el('line',{x1:padL,x2:W-padR,y1:sy(t),y2:sy(t),class:t===0?'base':''},g); const tx=el('text',{x:padL-8,y:sy(t)+4,'text-anchor':'end',class:'axis'},svg); tx.textContent=fmtM(t); });
  rows.forEach((r,i)=>{ const tx=el('text',{x:sx(i),y:H-bottom+18,'text-anchor':'middle',class:'axis'},svg); tx.textContent=r.mes; });
  series.forEach(s=>{ const d=rows.map((r,i)=>(i?'L':'M')+sx(i)+' '+sy(r[s.key])).join(' '); el('path',{d:d,fill:'none',stroke:`var(${s.color})`,'stroke-width':2,'stroke-linejoin':'round'},svg);
    rows.forEach((r,i)=>{ const c=el('circle',{cx:sx(i),cy:sy(r[s.key]),r:i===rows.length-1?5:3.5,fill:`var(${s.color})`,stroke:'var(--surface)','stroke-width':2},svg); });
  });
  // hover columns
  rows.forEach((r,i)=>{ const x0=i===0?padL:(sx(i-1)+sx(i))/2, x1=i===rows.length-1?W-padR:(sx(i)+sx(i+1))/2;
    const hit=el('rect',{x:x0,y:top,width:x1-x0,height:H-top-bottom,class:'hit'},svg);
    const line=el('line',{x1:sx(i),x2:sx(i),y1:top,y2:H-bottom,stroke:'var(--hair)',style:'display:none'},svg);
    hit.addEventListener('mouseenter',e=>{ line.style.display='block'; showTip(e,`<b>${r.mes} 2026</b>${series.map(s=>s.name+': '+fmt.format(r[s.key])).join('<br>')}<br>Cobrado/prorrateado: ${pct(r.cobrado/r.a_cobrar,0)}`); });
    hit.addEventListener('mousemove',moveTip); hit.addEventListener('mouseleave',()=>{ line.style.display='none'; hideTip(); });
  });
  // end labels
  series.forEach((s,si)=>{ const last=rows[rows.length-1]; const t=el('text',{x:sx(rows.length-1)+8,y:sy(last[s.key])+4+(si===1?10:si===2?-8:0),class:'val'},svg); t.textContent=fmtM(last[s.key]); });
  $('#evol').innerHTML=''; $('#evol').appendChild(svg);
})();
}
drawAll();
let lastW = innerWidth, rt; addEventListener('resize', ()=>{ clearTimeout(rt); rt=setTimeout(()=>{ if(Math.abs(innerWidth-lastW)>40){ lastW=innerWidth; drawAll(); } },150); });

// ---------- estado de cuentas
const states=[...new Set(D.units.map(u=>u.estado))];
$('#st').innerHTML += states.map(s=>`<option>${esc(s)}</option>`).join('');
function stateClass(s){ return s.startsWith('Moroso - sin')?'crit':s.startsWith('Moroso')?'ser':s.includes('recargo')?'warn':s.includes('favor')?'ok':''; }
function renderUnits(){
  const q=$('#q').value.trim().toLowerCase(), st=$('#st').value;
  const rows=D.units.filter(u=>(!st||u.estado===st)&&(!q||(u.propietario+' '+u.piso_depto+' '+u.uf).toLowerCase().includes(q)));
  $('#units tbody').innerHTML=rows.map(u=>`<tr><td class="mut">${u.uf}</td><td>${u.piso_depto}</td><td>${esc(u.propietario)}</td><td class="r">${fmt.format(u.saldo_ant)}</td><td class="r">${u.pagos?fmt.format(u.pagos):'<span class="mut">—</span>'}</td><td class="r">${u.deuda?fmt.format(u.deuda):'<span class="mut">—</span>'}</td><td class="r">${u.interes?fmt.format(u.interes):'<span class="mut">—</span>'}</td><td class="r">${u.pct_A.toFixed(2).replace('.',',')}%</td><td class="r">${fmt.format(u.total_mes)}</td><td class="r"><b>${fmt.format(u.a_pagar)}</b></td><td><span class="pill ${stateClass(u.estado)}">${esc(u.estado)}</span></td></tr>`).join('');
  const sum=k=>rows.reduce((s,u)=>s+u[k],0);
  $('#units tfoot').innerHTML=`<tr><td colspan="3">Total (${rows.length} unidades)</td><td class="r">${fmt.format(sum('saldo_ant'))}</td><td class="r">${fmt.format(sum('pagos'))}</td><td class="r">${fmt.format(sum('deuda'))}</td><td class="r">${fmt.format(sum('interes'))}</td><td class="r">${(rows.reduce((s,u)=>s+u.pct_A,0)).toFixed(1).replace('.',',')}%</td><td class="r">${fmt.format(sum('total_mes'))}</td><td class="r">${fmt.format(sum('a_pagar'))}</td><td></td></tr>`;
  $('#cnt').textContent=`${rows.length} de ${D.units.length} unidades`;
}
$('#q').addEventListener('input',renderUnits); $('#st').addEventListener('change',renderUnits); renderUnits();

// ---------- sueldos
$('#emp').innerHTML = D.sueldos.map(s=>`<div class="card"><h3>${esc(s.empleado)}</h3><div class="note">${esc(s.cargo)} · CUIL ${s.cuil} · período ${s.periodo}</div><div class="kv">${s.items.filter(i=>i[2]>0).map(i=>`<span>${esc(i[0])}${i[1]>1&&i[1]<100?` <span style="color:var(--muted)">× ${i[1]}</span>`:''}</span><span class="num">${fmt.format(i[2])}</span>`).join('')}<span class="t">Bruto</span><span class="t num">${fmt.format(s.bruto)}</span><span>Deducciones (aportes, obra social, sindicato)</span><span class="num" style="color:var(--critical)">−${fmt.format(s.deducciones)}</span><span class="t">Neto pagado</span><span class="t num">${fmt.format(s.neto)}</span></div></div>`).join('');
})();
</script>
"""
html = HTML.replace("__DATA__", DATA.replace("</", "<\\/"))
open(SC + "expensas-rivadavia-2069.html", "w", encoding="utf-8").write(html)
print("html", len(html))
