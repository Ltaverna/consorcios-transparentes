import os
HERE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(HERE, "datos") + "/"
PRIVADO = os.environ.get("CT_PRIVADO", os.path.expanduser("~/consorcio-transparente-privado")) + "/"
import re, json, itertools
from datetime import date

TXT = DATOS + "exp.txt"

def d(s):  # "dd-mm-yyyy" -> date
    dd, mm, yy = s.split("-"); return date(int(yy), int(mm), int(dd))

# ---------------------------------------------------------------- GASTOS (transcritos y validados contra totales del PDF)
# (categoria, proveedor, concepto, columna, importe, fecha_factura, nro_factura, importe_factura, fecha_pago, forma, periodo)
G = [
 ("SUELDOS Y CARGAS SOCIALES","ARCA","Retención SIRE IVA s/ FC 4833 Cooperativa C.S.I. (junio 2026)","A",256260.11,None,None,None,"05-08-2026","Transferencia","Junio 2026"),
 ("SUELDOS Y CARGAS SOCIALES","ARCA","F.931 contribuciones y aportes seg. social, obra social, LRT, SCVO","A",1920211.16,None,None,None,"10-08-2026","Transferencia","Junio 2026"),
 ("SUELDOS Y CARGAS SOCIALES","FATERYH","Aporte y contribución solidaria OS CCT 589/10 art. 27 bis","A",365166.81,None,None,None,"12-08-2026","Débito automático","Julio 2026"),
 ("SUELDOS Y CARGAS SOCIALES","SERACARH","Contribución","A",20490.98,None,None,None,"12-08-2026","Débito automático","Julio 2026"),
 ("SUELDOS Y CARGAS SOCIALES","SUTERH","Aporte, contribución y cuota sindical","A",184418.86,None,None,None,"12-08-2026","Débito automático","Julio 2026"),
 ("SUELDOS Y CARGAS SOCIALES","Consorcio Rivadavia 2069 (sueldos)","Sueldo neto Heres Miguel Ángel - Ayudante permanente s/vivienda (recibo 584766)","A",1424799.00,None,None,None,"04-08-2026","Transferencia","Julio 2026"),
 ("SUELDOS Y CARGAS SOCIALES","Consorcio Rivadavia 2069 (sueldos)","Sueldo neto Gonzales Ramón - Encargado permanente c/vivienda (recibo 584774)","A",1774010.00,None,None,None,"04-08-2026","Transferencia","Julio 2026"),
 ("MANTENIMIENTOS EN UNIDADES","PEÑALOZA ALEJANDRO ROBERTO","Cambio columna vertical y horizontales de calefacción sector F pisos 8-12 c/albañilería. Final anticipo + cuota 1/3 (obra total $14.000.000)","D",4333333.33,"12-08-2026","00003-00000202",9000000.00,"12-08-2026","Transferencia",None),
 ("MANTENIMIENTOS EN UNIDADES","SACZEWICZYK MARIA EUGENIA","Saldo colocación porcelanato ~50 m² en UF 13-B (total $4.552.000)","A",2552000.00,"27-07-2026","00001-00000007",4552000.00,"12-08-2026","Transferencia",None),
 ("MANTENIMIENTOS EN UNIDADES","SACZEWICZYK MARIA EUGENIA","Pintura, reparación de pared UF 13-B","A",700000.00,"31-08-2026","00001-00000008",700000.00,"31-08-2026","Transferencia",None),
 ("IMPUESTOS","AGIP-ABL","ABL partida 2813079","B",350657.78,None,None,None,"04-08-2026","Transferencia","Agosto 2026"),
 ("SERVICIOS PUBLICOS","EDESUR","Energía eléctrica 16/07 al 14/08/2026 (cliente 80052153)","A",1465080.20,"16-07-2026","9905-02077599",1465080.20,"13-08-2026","Transferencia",None),
 ("SERVICIOS PUBLICOS","METROGAS","Gas cliente 10821849500, liq. 1/2 bimestre 04/2026","D",3482893.85,"30-07-2026","0064-70457249",3482893.85,"10-08-2026","Débito automático","Agosto 2026"),
 ("SERVICIOS PUBLICOS","AYSA","Agua cuenta 1409553, 06/08 al 04/09/2026","B",236758.89,"11-07-2026","0111-20383378",236758.89,"10-08-2026","Débito automático",None),
 ("ABONOS Y SERVICIOS","ASCENSORES LAUFKEN","Abono ascensores julio","A",442000.00,"02-08-2026","31282",442000.00,"10-08-2026","Transferencia","Julio 2026"),
 ("ABONOS Y SERVICIOS","CERRAJERIA MATHEU","Service cierrapuertas puerta principal / hall a garaje","A",48000.00,"30-07-2026","00001-00000401",48000.00,"04-08-2026","Transferencia",None),
 ("ABONOS Y SERVICIOS","COOPERATIVA DE TRABAJO C.S.I.","Servicio de seguridad FC 4925 mes julio (total $3.166.031,55 menos retención SIRE IVA $274.811,54)","A",2891220.01,None,"4925",3166031.55,"21-08-2026","Transferencia","Junio 2026 (sic)"),
 ("ABONOS Y SERVICIOS","DESTAPACIONES EL LEON","Abono destapaciones agosto","A",416200.00,"03-08-2026","8675",416200.00,"11-08-2026","Transferencia","Agosto 2026"),
 ("ABONOS Y SERVICIOS","FLOW","Internet cámaras agosto","A",80440.21,None,None,None,"10-08-2026","Transferencia","Agosto 2026"),
 ("ABONOS Y SERVICIOS","GESTION CONTINUA","Medición certificada puesta a tierra / continuidad de masas","A",313000.00,"18-08-2026","00005-00051325",313000.00,"27-08-2026","Transferencia",None),
 ("ABONOS Y SERVICIOS","GESTION CONTINUA","Declaración jurada anual CABA 2025","A",305000.00,"07-08-2026","51300",305000.00,"27-08-2026","Transferencia",None),
 ("ABONOS Y SERVICIOS","GRUPO CONTROLSEG","Abono control de acceso agosto","A",55000.00,"01-08-2026","00002-00037163",55000.00,"04-08-2026","Transferencia","Agosto 2026"),
 ("ABONOS Y SERVICIOS","MAGNUM FUMIGACIONES (Escuchuri)","Abono desinsectación / desratización agosto","A",233000.00,"09-08-2026","6494",233000.00,"09-08-2026","Transferencia","Agosto 2026"),
 ("ABONOS Y SERVICIOS","MARIO LEONARDO ROTH","Certificación de equipos térmicos agosto","D",90000.00,"12-08-2026","4417",90000.00,"18-08-2026","Transferencia","Agosto 2026"),
 ("ABONOS Y SERVICIOS","MARIO LEONARDO ROTH","Cambio serpentina calefacción 12-B ($2.900.000) + cupla 1º ($150.000) + serpentina 13-B ($4.900.000). Cuota de 3 (total $7.950.000)","D",2650000.00,"29-05-2026","4182 / 4183 / 4191",7950000.00,"21-08-2026","Transferencia",None),
 ("ABONOS Y SERVICIOS","MATHIL","Abono mant. matafuegos Res. 405/AGC/19 - DICIEMBRE 2025","A",75000.00,"01-12-2025","0008-00033655",75000.00,"09-08-2026","Transferencia","Diciembre 2025"),
 ("ABONOS Y SERVICIOS","MATHIL","Abono mant. matafuegos Res. 405/AGC/19 - NOVIEMBRE 2025","A",75000.00,"07-11-2025","0008-00033304",75000.00,"09-08-2026","Transferencia","Noviembre 2025"),
 ("ABONOS Y SERVICIOS","METROGAS","Gas cliente 10614995000, liq. 1/2 bimestre 04/2026","D",43014.59,"30-07-2026","0064-70504785",43014.59,"10-08-2026","Débito automático",None),
 ("ABONOS Y SERVICIOS","SOLUCIONES EN EXTINGUIDORES S.R.L.","Mant. instalación Res. 405/AGC/19 Anexo IV","A",99750.74,"07-08-2026","00002-00002612",99750.74,"11-08-2026","Transferencia",None),
 ("GASTOS CONTABLES","LUIS BELTRAN MONTASTRUC","Honorarios liquidación sueldos, DDJJ cargas sociales, SIRE/SICORE","A",84900.00,"11-08-2026","1167",84900.00,"11-08-2026","Transferencia","Julio 2026"),
 ("MANTENIMIENTO DE PARTES COMUNES","LEV RENTAL SRL","Bomba sumergible desagote 1.5HP. Factura B a nombre de Hermelinda Rosana Acosta (13-B); el consorcio le transfirió el importe a su cuenta el 12-08 (reintegro)","A",205392.00,"03-08-2026","0021-00028257",205392.00,"12-08-2026","Transferencia",None),
 ("GASTOS BANCARIOS","BANCO DE GALICIA","Gastos bancarios 21/07 al 21/08/2026","A",452336.93,None,None,None,"21-08-2026","Débito automático","Agosto 2026"),
 ("GASTOS DE LIMPIEZA","SOLVER","Artículos de limpieza (lavandina, limpiadores, bolsas, etc.)","A",259944.00,"31-03-2026","00002-00014560",259944.00,"04-08-2026","Transferencia",None),
 ("GASTOS DE ADMINISTRACION","GRACIELA MARTA CROCAMO","Disposición 856 GCBA: escaneo y subida de documentación","A",99000.00,None,None,None,"28-08-2026","Transferencia","Agosto 2026"),
 ("GASTOS DE ADMINISTRACION","GRACIELA MARTA CROCAMO","Honorarios administración agosto","A",775799.00,"18-08-2026","1642",775799.00,"28-08-2026","Transferencia","Agosto 2026"),
 ("SEGUROS","ALLIANZ SEGUROS","Póliza integral 250230772503 - cuota 8/10","A",268652.00,None,None,None,"06-08-2026","Débito automático",None),
 ("SEGUROS","ALLIANZ SEGUROS","Póliza 250230772503 endoso 1 (RC 39,9M) - cuota 5/7","A",8128.00,None,None,None,"06-08-2026","Débito automático",None),
 ("SEGUROS","ALLIANZ SEGUROS","Póliza 250230772503 endoso 2 (RC 650,1M) - cuota 4/6","A",382377.00,None,None,None,"06-08-2026","Débito automático",None),
 ("SEGUROS","BERKLEY CIA DE SEGUROS","Seguro de vida colectivo 2 vidas póliza 17-35287 - cuota 7/10","A",39711.71,None,None,None,"05-08-2026","Débito automático",None),
 ("GASTOS GENERALES","KEVIN LUCAS AVALOS","Arreglo cámaras","A",70000.00,"22-07-2026","00001-00000005",70000.00,"01-08-2026","Efectivo (Caja)",None),
 ("GASTOS GENERALES","NAVARRO FERNANDEZ RICARDO ESTEBAN","Honorarios contestación carta documento","A",135000.00,"29-07-2026","00003-00000268",135000.00,"10-08-2026","Transferencia",None),
 ("GASTOS GENERALES","NAVARRO FERNANDEZ RICARDO ESTEBAN","Anticipo mediación con propietario UF 68 (10-E)","A",29000.00,None,None,None,"12-08-2026","Transferencia",None),
 ("GASTOS GENERALES","REDCONAR","Plataforma sistema de gestión","A",183976.00,"07-08-2026","00001-00053308",183976.00,"12-08-2026","Débito automático",None),
]
gastos = []
for i, r in enumerate(G, 1):
    cat, prov, con, col, imp, ff, nf, impf, fp, forma, per = r
    dias = (d(fp) - d(ff)).days if ff else None
    gastos.append(dict(n=i, categoria=cat, proveedor=prov, concepto=con, columna=col, importe=imp,
                       fecha_factura=ff, nro_factura=nf, importe_factura=impf, fecha_pago=fp, forma=forma,
                       periodo=per, dias_factura_pago=dias))
TOTAL_GASTOS = 29876923.16
assert abs(sum(g["importe"] for g in gastos) - TOTAL_GASTOS) < 0.01, sum(g["importe"] for g in gastos)
for col, tot in (("A",18690264.72),("B",587416.67),("D",10599241.77)):
    assert abs(sum(g["importe"] for g in gastos if g["columna"]==col) - tot) < 0.01, col
CAT_TOT = {"ABONOS Y SERVICIOS":7816625.55,"MANTENIMIENTOS EN UNIDADES":7585333.33,"SUELDOS Y CARGAS SOCIALES":5945356.92,
 "SERVICIOS PUBLICOS":4947974.05+236758.89,"GASTOS DE ADMINISTRACION":874799.00,"SEGUROS":698868.71,"GASTOS BANCARIOS":452336.93,
 "GASTOS GENERALES":417976.00,"IMPUESTOS":350657.78,"GASTOS DE LIMPIEZA":259944.00,"MANTENIMIENTO DE PARTES COMUNES":205392.00,"GASTOS CONTABLES":84900.00}
for c, t in CAT_TOT.items():
    assert abs(sum(g["importe"] for g in gastos if g["categoria"]==c) - t) < 0.01, c

# ---------------------------------------------------------------- UNIDADES (parseo del estado de cuentas)
txt = open(TXT, encoding="utf-8").read().splitlines()
tok = re.compile(r"\$ (-?[\d,]+\.\d{2})|(\d+\.\d{2})%")
row_re = re.compile(r"^\s*(\d{1,3})\s+(LOC-|PB-E|\d{1,2}-[A-G]|UC-\d{1,2})\s+(.+?)\s+(\$ .*?)\s+\1\s*$")
units = []
for line in txt:
    m = row_re.match(line)
    if not m: continue
    uf, pd_, prop, rest = m.groups()
    seq = []
    for mm in tok.finditer(rest):
        if mm.group(1) is not None: seq.append(("$", float(mm.group(1).replace(",", ""))))
        else: seq.append(("%", float(mm.group(2))))
    saldo = seq[0][1]
    # middle: between saldo and first %
    first_pct = next(i for i, t in enumerate(seq) if t[0] == "%")
    M = [t[1] for t in seq[1:first_pct]]
    tail = seq[first_pct:]
    pct_pairs = []  # (pct, amount)
    i = 0
    while i < len(tail) and tail[i][0] == "%":
        pct_pairs.append((tail[i][1], tail[i+1][1])); i += 2
    rest_amts = [t[1] for t in tail[i:]]
    if len(rest_amts) == 3: total, red, apagar = rest_amts
    elif len(rest_amts) == 2: total, apagar = rest_amts; red = 0.0
    else: raise ValueError(line)
    is_uc = pd_.startswith("UC")
    if is_uc:
        (pa, a), (pb, b) = pct_pairs; pdd, dd = 0.0, 0.0
    else:
        (pa, a), (pdd, dd) = pct_pairs; pb, b = 0.0, 0.0
    assert abs(a + b + dd - total) < 0.02, line
    # resolve M -> (pagos, cred, deuda, int)
    sol = None
    for pos in itertools.combinations(range(4), len(M)):
        v = [0.0]*4
        for p, val in zip(pos, M): v[p] = val
        pagos, cred, deuda, inte = v
        if abs(saldo - pagos + cred - deuda) < 0.02 and abs(total + deuda + inte + red - apagar) < 0.02:
            sol = v; break
    assert sol is not None, (line, M)
    pagos, cred, deuda, inte = sol
    units.append(dict(uf=int(uf), piso_depto=pd_, propietario=prop.strip(), tipo="Cochera" if is_uc else ("Local" if pd_=="LOC-" else "Departamento"),
                      saldo_ant=saldo, pagos=pagos, cred_deb=cred, deuda=deuda, interes=inte,
                      pct_A=pa, exp_A=a, pct_B=pb, exp_B=b, pct_D=pdd, exp_D=dd, total_mes=total, redondeo=red, a_pagar=apagar))
assert len(units) == 116, len(units)
T = dict(saldo_ant=34403411.91, pagos=30894682.83, cred_deb=18000.00, deuda=3526729.08, interes=535506.21,
         exp_A=20512710.00, exp_B=587415.99, exp_D=10605834.61, total_mes=31705960.60, redondeo=41.02, a_pagar=35768236.91)
for k, v in T.items():
    s = sum(u[k] for u in units); assert abs(s - v) < 0.05, (k, s, v)

deudores_pdf = {23:644682.23,24:200000.00,27:18000.00,31:227857.31,35:258849.35,37:60000.00,55:829878.55,78:363253.78,201:1425249.01}
for u in units:
    if u["deuda"] > 0: assert abs(deudores_pdf[u["uf"]] - u["deuda"]) < 0.01
    u["meses_deuda"] = round(u["deuda"] / u["total_mes"], 2) if u["deuda"] > 0 else 0
    u["tasa_int_sobre_deuda"] = round(u["interes"] / u["deuda"], 4) if u["deuda"] > 0 and u["interes"] > 0 else None
    u["tasa_int_sobre_saldo_ant"] = round(u["interes"] / u["saldo_ant"], 4) if u["interes"] > 0 and u["saldo_ant"] > 0 else None
    u["pago_pct_saldo"] = round(u["pagos"] / u["saldo_ant"], 4) if u["saldo_ant"] > 0 else None
    if u["deuda"] > 0 and u["pagos"] == 0: u["estado"] = "Moroso - sin pago en el mes"
    elif u["deuda"] > 0 and u["uf"] == 27: u["estado"] = "Débito particular (llavero), no mora"
    elif u["deuda"] > 0: u["estado"] = "Moroso - pago parcial"
    elif u["deuda"] < 0 and u["interes"] > 0: u["estado"] = "Al día - pagó con recargo (compensado)"
    elif u["deuda"] < 0: u["estado"] = "Saldo a favor"
    elif u["interes"] > 0: u["estado"] = "Al día - pagó fuera de término (recargo)"
    else: u["estado"] = "Al día"

# ---------------------------------------------------------------- Otros bloques
evol = [("Marzo 2026",21230111.67,22957337.77,21106008.12),("Abril 2026",21235633.48,16429951.61,21825519.12),
        ("Mayo 2026",23897542.24,20717051.97,19391756.78),("Junio 2026",21631133.72,20199290.17,27014721.69),
        ("Julio 2026",31122626.83,32543124.90,21466527.20),("Agosto 2026",31705960.60,29876923.16,30894682.83)]
evolucion = [dict(mes=m, a_cobrar=a, gastos=g, cobrado=c, cobrado_vs_prorrateo=round(c/a,4), gastos_vs_prorrateo=round(g/a,4)) for m,a,g,c in evol]

estado_fin = dict(saldo_anterior=923626.64, ing_termino=28388508.69, ing_adeudadas=2224515.54, ing_intereses=234785.54,
                  ing_adelantadas=46873.06, egresos=29876923.16, saldo_cierre=1941386.31)
composicion = [dict(cuenta="BANCO GALICIA 17758-6 001-1", saldo_ant=882050.53, ingresos=29550976.89, egresos=29806923.16, saldo_cierre=626104.26),
               dict(cuenta="CAJA (efectivo)", saldo_ant=41576.11, ingresos=1343705.94, egresos=70000.00, saldo_cierre=1315282.05)]
patrimonial = dict(disponibilidades=1941386.31, a_cobrar=35768236.91, devengados_pend=0.0, facturas_pend=-4806666.67, total=32902956.55)

sueldos = [
 dict(empleado="Heres, Miguel Ángel", cuil="20-21804903-7", cargo="Ayudante permanente sin vivienda", periodo="Julio 2026",
      items=[("Sueldo básico",1.00,1375401.00,0),("Antigüedad reconocida (años)",9.00,206309.70,0),("Adicional viáticos",1,83083.10,0),
             ("Horas extras 50%",2.00,25453.06,0),("Adicional ajuste junio",1,75582.10,0),("Adicional (s/detalle)",1,55000.00,0),
             ("D.N.R.P. Jubilación 11%",0.11,0,200291.19),("Ley 19.032 3%",0.03,0,54624.87),("Obra social 3%",0.03,0,54624.87),
             ("Caja protección familia 1%",0.01,0,18208.29),("Cuota sindical 2%",0.02,0,36416.58),("Fondo matern./vida/desemp. 1%",0.01,0,18208.29),
             ("Seguro vitalicio art. 27 bis 0,75%",0.0075,0,13656.22)], bruto=1820828.96, deducciones=396030.31, neto=1424799.00),
 dict(empleado="Gonzales, Ramón", cuil="23-12724113-9", cargo="Encargado permanente con vivienda", periodo="Julio 2026",
      items=[("Sueldo básico",1.00,1197409.00,0),("Antigüedad reconocida (años)",12.00,275079.60,0),("Retiro de residuos por unidad (95 u.)",95,207679.50,0),
             ("Clasificación de residuos",1,75305.00,0),("Plus limpieza de cocheras",1,29832.30,0),("Horas extras 50%",23.00,318837.96,0),
             ("Valor vivienda",1,8031.10,0),("Adicional ajuste junio 2026",1,110193.48,0),("Adicional (s/detalle)",1,55000.00,0),
             ("D.N.R.P. Jubilación 11%",0.11,0,250510.47),("Ley 19.032 3%",0.03,0,68321.04),("Obra social 3%",0.03,0,68321.04),
             ("Caja protección familia 1%",0.01,0,22773.68),("Cuota sindical 2%",0.02,0,45547.36),("Fondo matern./vida/desemp. 1%",0.01,0,22773.68),
             ("Seguro vitalicio art. 27 bis 0,75%",0.0075,0,17080.26),("Valor vivienda (deducción)",1,0,8031.10)], bruto=2277367.94, deducciones=503358.63, neto=1774010.00),
]
for s in sueldos:
    assert abs(sum(i[2] for i in s["items"]) - s["bruto"]) < 0.02, s["empleado"]
    assert abs(sum(i[3] for i in s["items"]) - s["deducciones"]) < 0.02, s["empleado"]

proveedores = [
 ("AGIP-ABL","AGIP-ABL","",""),("AYSA","AGUA Y SANEAMIENTOS ARGENTINOS S.A.","30-70956507-5","Tucumán 752, CABA"),
 ("DESTAPACIONES EL LEON","AGUIRRE EDUARDO JAVIER","23-25748140-9","Libertad 3983, Buenos Aires"),
 ("ALLIANZ SEGUROS","ALLIANZ ARGENTINA CIA. DE SEGUROS S.A.","30-50003721-7","Av. Corrientes 299, CABA"),
 ("ARCA","ARCA - Agencia de Recaudación y Control Aduanero","",""),("ASCENSORES LAUFKEN","ASCENSORES LAUFKEN S.R.L.","30-71458951-9","Uruguay 772, CABA"),
 ("BANCO DE GALICIA","BANCO DE GALICIA","",""),("BERKLEY CIA DE SEGUROS","BERKLEY CIA DE SEGUROS","",""),
 ("FLOW","CABLEVISION S.A.","30-57365208-4","General Hornos 690, CABA"),("COOPERATIVA DE TRABAJO C.S.I.","COOPERATIVA DE TRABAJO C.S.I. LIMITADA","30-66300195-3","CABA"),
 ("Consorcio Rivadavia 2069 (sueldos)","Consorcio RIVADAVIA 2069","33-60039145-9",""),("EDESUR","EDESUR S.A.","30-65511651-2","San José 190, CABA"),
 ("MAGNUM FUMIGACIONES (Escuchuri)","ESCUCHURI MARCELO LUIS","20-21008101-2","Salta 1957, CABA"),("FATERYH","FATERYH","",""),
 ("GESTION CONTINUA","GESTION CONTINUA S.A.","30-71504440-0","La Pampa 1534, CABA"),
 ("GRACIELA MARTA CROCAMO","GRACIELA MARTA CROCAMO (= Administración Almazare)","27-06254638-2","Adolfo Alsina 1957, CABA"),
 ("GRUPO CONTROLSEG","GRUPO CONTROLSEG S.A.","30-71767663-3","Av. Rivadavia 2151, CABA"),
 ("LEV RENTAL SRL","LEV RENTAL SRL (Madariaga 6422, Villa Riachuelo). La liquidación pone como razón social a la compradora, Hermelinda Rosana Acosta, propietaria de 13-B","30-71212174-9",""),
 ("KEVIN LUCAS AVALOS","KEVIN LUCAS AVALOS","20-35784511-5","CABA"),("LUIS BELTRAN MONTASTRUC","LUIS BELTRAN MONTASTRUC","20-16847958-2","Chacabuco 732 9° 49, CABA"),
 ("CERRAJERIA MATHEU","LUIS MIGUEL RODRIGUEZ MONTILLA","20-95935741-3","CABA"),("MARIO LEONARDO ROTH","MARIO LEONARDO ROTH","20-16252593-0","Buenos Aires"),
 ("MATHIL","METALURGICA LARRAUDE S.A. - MATHIL MATAFUEGOS","30-70738288-7","Av. del Barco Centenera 2946, CABA"),
 ("METROGAS","METROGAS S.A.","30-65786367-6","Gral. Gregorio Aráoz de Lamadrid 1360, CABA"),
 ("NAVARRO FERNANDEZ RICARDO ESTEBAN","NAVARRO FERNANDEZ RICARDO ESTEBAN","20-21873257-8",""),
 ("PEÑALOZA ALEJANDRO ROBERTO","PEÑALOZA ALEJANDRO ROBERTO","20-22554298-9","Buenos Aires"),
 ("REDCONAR","REDCONAR SRL","30-71609328-6","Scalabrini Ortiz 1024, CABA"),("SACZEWICZYK MARIA EUGENIA","SACZEWICZYK MARIA EUGENIA","27-27086831-8",""),
 ("SERACARH","SERACARH","",""),("SOLUCIONES EN EXTINGUIDORES S.R.L.","SOLUCIONES EN EXTINGUIDORES S.R.L.","30-71903002-1",""),
 ("SOLVER","SOLUCIONES VERTICALES SOLVER S.R.L.","30-71848714-1","CABA"),("SUTERH","SUTERH","",""),
]
prov_tot = {}
for g in gastos: prov_tot[g["proveedor"]] = prov_tot.get(g["proveedor"], 0) + g["importe"]
proveedores = [dict(fantasia=f, razon_social=r, cuit=c, direccion=a, pagado_mes=round(prov_tot.get(f, 0), 2), lineas=sum(1 for g in gastos if g["proveedor"]==f)) for f, r, c, a in proveedores]
assert abs(sum(p["pagado_mes"] for p in proveedores) - TOTAL_GASTOS) < 0.01


# ---------------------------------------------------------------- JULIO 2026 (mes anterior, para contraste)
# (categoria, proveedor, concepto, columna, importe, fecha_factura, fecha_pago, forma)
GJ = [
 ("SUELDOS Y CARGAS SOCIALES","ARCA","Retención SIRE IVA s/ FC 4776 Cooperativa C.S.I. (mayo 2026)","A",255132.48,None,"02-07-2026","Transferencia"),
 ("SUELDOS Y CARGAS SOCIALES","ARCA","F.931 contribuciones y aportes - período Mayo 2026","A",3066158.25,None,"15-07-2026","Transferencia"),
 ("SUELDOS Y CARGAS SOCIALES","FATERYH","Aporte y contribución solidaria - Junio 2026","A",570647.58,None,"13-07-2026","Transferencia"),
 ("SUELDOS Y CARGAS SOCIALES","SERACARH","Contribución - Junio 2026","A",32721.20,None,"13-07-2026","Transferencia"),
 ("SUELDOS Y CARGAS SOCIALES","SUTERH","Aporte y cuota sindical - Junio 2026","A",294490.78,None,"13-07-2026","Transferencia"),
 ("SUELDOS Y CARGAS SOCIALES","Consorcio Rivadavia 2069 (sueldos)","Sueldo + SAC Heres Miguel Ángel - Junio 2026","A",2370332.00,None,"01-07-2026","Transferencia"),
 ("SUELDOS Y CARGAS SOCIALES","Consorcio Rivadavia 2069 (sueldos)","Sueldo + SAC Gonzales Ramón - Junio 2026","A",2750537.00,None,"01-07-2026","Transferencia"),
 ("MANTENIMIENTOS EN UNIDADES","GOMEZ PABLO RODOLFO","Mampostería y colocación de venecitas en UF 14-F","A",320000.00,"01-07-2026","02-07-2026","Transferencia"),
 ("MANTENIMIENTOS EN UNIDADES","LO & CO S.A.","Porcelanato 60x120 Strazza para UF 13-B (material)","A",2003457.01,"11-07-2026","11-07-2026","Efectivo (Caja)"),
 ("MANTENIMIENTOS EN UNIDADES","LOPEZ RAMIREZ VIDAL","Lijado y plastificado de pisos UF 12-B (saldo de $400.000)","A",200000.00,"23-06-2026","01-07-2026","Transferencia"),
 ("MANTENIMIENTOS EN UNIDADES","PEÑALOZA ALEJANDRO ROBERTO","Anticipo acopio materiales columna calefacción sector F (8-F a 12-F). Factura 24-07 pagada 13-07","A",5000000.00,"24-07-2026","13-07-2026","Transferencia"),
 ("MANTENIMIENTOS EN UNIDADES","SACZEWICZYK MARIA EUGENIA","Pago a cuenta porcelanato UF 13-B (total $4.552.000)","A",2000000.00,"27-07-2026","23-07-2026","Efectivo (Caja)"),
 ("MANTENIMIENTOS EN UNIDADES","VARAS GILBERTO GABRIEL","Cambio columna agua fría entrepiso a UF 14-E y alimentación baño UF 14-F","A",680000.00,"30-06-2026","02-07-2026","Transferencia"),
 ("IMPUESTOS","AGIP-ABL","ABL partida 2813079 - Julio","B",350657.78,None,"02-07-2026","Transferencia"),
 ("SERVICIOS PUBLICOS","EDESUR","Energía 11/06 al 15/07/2026 (cliente 80052153)","A",1582033.54,"15-07-2026","20-07-2026","Transferencia"),
 ("SERVICIOS PUBLICOS","METROGAS","Gas cuenta principal, liq. 2/2 bimestre 03/2026","D",373073.82,"30-06-2026","13-07-2026","Débito automático"),
 ("SERVICIOS PUBLICOS","AYSA","Agua 07/07 al 05/08/2026","B",229965.57,"06-06-2026","06-07-2026","Débito automático"),
 ("SERVICIOS PUBLICOS","EDESUR","Energía cliente 50788 medidor 4570615","A",255952.30,"15-07-2026","30-07-2026","Débito automático"),
 ("ABONOS Y SERVICIOS","ASCENSORES LAUFKEN","Abono ascensores junio","A",442000.00,"02-07-2026","10-07-2026","Transferencia"),
 ("ABONOS Y SERVICIOS","ASCENSORES LAUFKEN","Ascensor 4: saldo 50% reparación de puerta (presup. 40595)","A",605000.00,"02-07-2026","10-07-2026","Transferencia"),
 ("ABONOS Y SERVICIOS","COOPERATIVA DE TRABAJO C.S.I.","Seguridad FC 44833 junio (total $2.952.305,40 menos ret. $256.260,11)","A",2696045.29,None,"29-07-2026","Efectivo (Caja)"),
 ("ABONOS Y SERVICIOS","DESTAPACIONES EL LEON","Abono destapaciones julio","A",389000.00,"01-07-2026","03-07-2026","Transferencia"),
 ("ABONOS Y SERVICIOS","FLOW","Internet cámaras julio","A",78966.19,None,"02-07-2026","Transferencia"),
 ("ABONOS Y SERVICIOS","GRUPO CONTROLSEG","Abono control de acceso julio","A",55000.00,"01-07-2026","02-07-2026","Transferencia"),
 ("ABONOS Y SERVICIOS","MAGNUM FUMIGACIONES (Escuchuri)","Abono desinsectación abril (2 visitas) / desratización","A",229000.00,"14-07-2026","10-07-2026","Transferencia"),
 ("ABONOS Y SERVICIOS","MARIO LEONARDO ROTH","Certificación de equipos térmicos julio","A",90000.00,"16-07-2026","20-07-2026","Transferencia"),
 ("ABONOS Y SERVICIOS","MARIO LEONARDO ROTH","Serpentinas 12-B / 13-B + cupla. Cuota de 3 (total $7.950.000)","D",2650000.00,"29-05-2026","13-07-2026","Transferencia"),
 ("ABONOS Y SERVICIOS","METROGAS","Gas cuenta secundaria, liq. 2/2 bimestre 03/2026","A",39970.43,"30-06-2026","13-07-2026","Débito automático"),
 ("ABONOS Y SERVICIOS","SOLUCIONES EN EXTINGUIDORES S.R.L.","Mant. instalación Res. 405/AGC/19 Anexo IV","A",93224.99,"08-07-2026","16-07-2026","Transferencia"),
 ("GASTOS CONTABLES","LUIS BELTRAN MONTASTRUC","Honorarios liquidación sueldos y DDJJ - junio","A",79600.00,"15-07-2026","10-07-2026","Transferencia"),
 ("GASTOS CONTABLES","LUIS BELTRAN MONTASTRUC","Rúbrica libro sueldo digital 09-2025 a 03-2026","A",56000.00,"07-05-2026","17-07-2026","Transferencia"),
 ("GASTOS BANCARIOS","BANCO DE GALICIA","Gastos bancarios 22/06 al 21/07/2026","A",394545.83,None,"21-07-2026","Débito automático"),
 ("GASTOS DE LIMPIEZA","SOLVER","Artículos de limpieza y lámparas","A",359992.00,"06-07-2026","07-07-2026","Transferencia"),
 ("GASTOS DE ADMINISTRACION","GRACIELA MARTA CROCAMO","Disposición 856: escaneo y subida de documentación - julio","A",95000.00,None,"28-07-2026","Transferencia"),
 ("GASTOS DE ADMINISTRACION","GRACIELA MARTA CROCAMO","Honorarios administración julio","A",711980.00,"22-07-2026","28-07-2026","Transferencia"),
 ("SEGUROS","ALLIANZ SEGUROS","Póliza integral - cuota 7/10","A",268652.00,None,"06-07-2026","Débito automático"),
 ("SEGUROS","ALLIANZ SEGUROS","Endoso 1 - cuota 4/7","A",8128.00,None,"06-07-2026","Débito automático"),
 ("SEGUROS","ALLIANZ SEGUROS","Endoso 2 (RC 650,1M) - cuota 3/6","A",382377.00,None,"06-07-2026","Débito automático"),
 ("SEGUROS","ALLIANZ SEGUROS","Endoso 5 cristales (suma $8,6M → $9M)","A",39136.15,None,"15-07-2026","Débito automático"),
 ("SEGUROS","BERKLEY CIA DE SEGUROS","Seguro de vida colectivo - cuota 6/10","A",39711.71,None,"03-07-2026","Débito automático"),
 ("GASTOS GENERALES","CENTRO GRÁFICO MAXICOPY","Artículos de librería","A",7200.00,"03-07-2026","03-07-2026","Efectivo (Caja)"),
 ("GASTOS GENERALES","CORREO ARGENTINO","Carta documento a UF PB-E","A",23900.00,"27-07-2026","27-07-2026","Efectivo (Caja)"),
 ("GASTOS GENERALES","NAVARRO FERNANDEZ RICARDO ESTEBAN","Patrocinio letrado en audiencia por denuncia en Defensa del Consumidor","A",200000.00,"03-07-2026","03-07-2026","Transferencia"),
 ("GASTOS GENERALES","REDCONAR","Plataforma sistema de gestión","A",173536.00,"07-07-2026","13-07-2026","Débito automático"),
]
gastos_jul = []
for i, r in enumerate(GJ, 1):
    cat, prov, con, col, imp, ff, fp, forma = r
    gastos_jul.append(dict(n=i, categoria=cat, proveedor=prov, concepto=con, columna=col, importe=imp, fecha_factura=ff, fecha_pago=fp, forma=forma,
                           dias_factura_pago=(d(fp)-d(ff)).days if ff else None))
TOTAL_JUL = 32543124.90
assert abs(sum(g["importe"] for g in gastos_jul) - TOTAL_JUL) < 0.01, sum(g["importe"] for g in gastos_jul)
for col, tot in (("A",28939427.73),("B",580623.35),("D",3023073.82)):
    assert abs(sum(g["importe"] for g in gastos_jul if g["columna"]==col) - tot) < 0.01, col
CAT_JUL = {"MANTENIMIENTOS EN UNIDADES":10203457.01,"SUELDOS Y CARGAS SOCIALES":9340019.29,"ABONOS Y SERVICIOS":7368206.90,"SERVICIOS PUBLICOS":1955107.36+485917.87,
 "GASTOS DE ADMINISTRACION":806980.00,"SEGUROS":738004.86,"GASTOS GENERALES":404636.00,"GASTOS BANCARIOS":394545.83,"GASTOS DE LIMPIEZA":359992.00,"IMPUESTOS":350657.78,"GASTOS CONTABLES":135600.00}
for c, t in CAT_JUL.items():
    assert abs(sum(g["importe"] for g in gastos_jul if g["categoria"]==c) - t) < 0.01, c
assert abs(sum(g["importe"] for g in gastos_jul if g["forma"].startswith("Efectivo")) - 6730602.30) < 0.01

estado_fin_jul = dict(saldo_anterior=12000224.34, ing_termino=18850757.09, ing_adeudadas=1060660.45, ing_intereses=172441.82,
                      ing_adelantadas=1382667.85, egresos=32543124.90, saldo_cierre=923626.64)
composicion_jul = [dict(cuenta="BANCO GALICIA 17758-6 001-1", saldo_ant=8151887.61, ingresos=18542685.52, egresos=25812522.60, saldo_cierre=882050.53),
                   dict(cuenta="CAJA (efectivo)", saldo_ant=3848336.73, ingresos=2923841.68, egresos=6730602.30, saldo_cierre=41576.11)]
patrimonial_jul = dict(disponibilidades=923626.64, a_cobrar=34403411.91, devengados_pend=0.0, facturas_pend=-5342000.00, total=29985038.55)
deudores_jul = [(1,"LOC-","SEGUROS EVOLUCION",592674.01),(23,"4-B","CONTRERAS",251728.23),(24,"4-A","ASOCARG J BASQUE",168311.24),(25,"4-C","MAZZOCONI",171601.25),
                (31,"5-A","SINGLAR",561744.31),(42,"6-F","CARBALLEDO",177169.42),(55,"8-D","SARFIEL CARLOS",546014.55),(78,"11-G","CATTANEO PEDRO",417676.78),
                (81,"12-C","LORES CARLOTA",170842.81),(201,"UC-1","DEL VALLE",1193442.01),(220,"UC-20","SEGURO EVOLUCION",32145.50)]
assert abs(sum(x[3] for x in deudores_jul) - 4283350.11) < 0.01
deudores_jul = [dict(uf=a, piso_depto=b, propietario=c, deuda=e) for a,b,c,e in deudores_jul]
ref_sep25 = dict(periodo="Septiembre 2025", gastos=20400218.20, sueldos=3992849.30, mant_unidades=1758173.82, metrogas_principal=2631571.74,
                 disponibilidades=7294814.32, banco=2498812.49, caja=4796001.83, facturas_pend=-265000.00)

# ---------------------------------------------------------------- OBRAS / GASTO POR UNIDAD FUNCIONAL (julio + agosto)
# (uf_beneficiaria, propietario, obra, proveedor, total_obra, pagado_jul, pagado_ago, columna, observación)
OBRAS = [
 ("13-B (UF 86)","ACOSTA ROSANA","Porcelanato: material 60x120 Strazza","LO & CO S.A.",2003457.01,2003457.01,0,"A","Pagado en efectivo"),
 ("13-B (UF 86)","ACOSTA ROSANA","Porcelanato: demolición y colocación ~50 m²","SACZEWICZYK MARIA EUGENIA",4552000.00,2000000.00,2552000.00,"A","$2 M en efectivo (jul). Factura N° 7 del proveedor"),
 ("13-B (UF 86)","ACOSTA ROSANA","Pintura y reparación de pared","SACZEWICZYK MARIA EUGENIA",700000.00,0,700000.00,"A","Factura N° 8, emitida y pagada el 31-08"),
 ("13-B (UF 86)","ACOSTA ROSANA","Cambio serpentina calefacción (caño pex 20 mm, 20 m)","MARIO LEONARDO ROTH",4900000.00,1633333.33,1633333.33,"D","Prorrateo de las 3 cuotas de $2.650.000 (61,6%); 1ª cuota presumiblemente en junio"),
 ("12-B (UF 79)","LOPEZ ARIAS","Cambio serpentina calefacción","MARIO LEONARDO ROTH",2900000.00,966666.67,966666.67,"D","Prorrateo de las 3 cuotas (36,5%)"),
 ("12-B (UF 79)","LOPEZ ARIAS","Lijado y plastificado de pisos","LOPEZ RAMIREZ VIDAL",400000.00,200000.00,0,"A","Saldo en julio; $200.000 en mes anterior"),
 ("Sector F pisos 8-12 (UF 56, 63, 70, 77, 84)","MAGNATERRA / GALLEGUILLO / DEL CAST / TIMMER / PALOMBO","Columna vertical y horizontales de calefacción + albañilería y yeso","PEÑALOZA ALEJANDRO ROBERTO",14000000.00,5000000.00,4333333.33,"A (jul) / D (ago)","Anticipo $5 M en columna A (cocheras pagaron); cuota en D (cocheras exentas). Factura de julio emitida después del pago. Pendiente $4.666.667"),
 ("14-F (UF 94)","CARRO","Mampostería y venecitas","GOMEZ PABLO RODOLFO",320000.00,320000.00,0,"A",""),
 ("14-E / 14-F (UF 92, 94)","CASOLA / CARRO","Cambio columna agua fría (galvanizado → termofusión)","VARAS GILBERTO GABRIEL",680000.00,680000.00,0,"A",""),
 ("Piso 1 (sin UF)","—","Reparación cupla para dar servicio","MARIO LEONARDO ROTH",150000.00,50000.00,50000.00,"D","Prorrateo de cuotas (1,9%)"),
 ("10-E (UF 68)","RODRIGUEZ ALEJANDRO","Anticipo mediación con el propietario","NAVARRO FERNANDEZ R. E.",29000.00,0,29000.00,"A","La UF 68 no tiene deuda: conflicto de otra naturaleza"),
 ("PB-E (UF 2)","CARLUCCIO STELLA","Carta documento","CORREO ARGENTINO",23900.00,23900.00,0,"A","Pagado en efectivo"),
 ("4-D (UF 27)","VALDES ARIEL","Llavero electrónico (Controlseg FC 37099)","GRUPO CONTROLSEG",18000.00,0,0,"Débito al propietario","Debitado a la UF, no lo paga el consorcio"),
 ("Partes comunes (reintegro a propietaria 13-B)","ACOSTA ROSANA","Bomba sumergible comprada por la propietaria a su nombre y reembolsada por el consorcio","LEV RENTAL SRL / reintegro a R. Acosta",205392.00,0,205392.00,"A","Factura a nombre de la propietaria; transferencia a su cuenta de Banco Nación"),
 ("Sin UF identificada","—","Contestación de carta documento","NAVARRO FERNANDEZ R. E.",135000.00,0,135000.00,"A",""),
 ("Sin UF identificada","—","Patrocinio en audiencia por denuncia en Defensa del Consumidor","NAVARRO FERNANDEZ R. E.",200000.00,200000.00,0,"A","Denuncia contra el consorcio / administración no informada"),
]
obras = [dict(uf=a, propietario=b, obra=c, proveedor=dd, total_obra=e, pagado_jul=f, pagado_ago=g, pagado_2m=round(f+g,2), pendiente=round(e-f-g,2), columna=h, obs=i)
         for a,b,c,dd,e,f,g,h,i in OBRAS]

meta = dict(consorcio="Consorcio de Propietarios Rivadavia 2069, Balvanera, CABA", cuit="33-60039145-9", periodo="Agosto 2026",
            administracion="Administración Almazare (Graciela Marta Crocamo, RPA 5911)", venc1="10-09-2026 (recargo 5%)", venc2="20-09-2026 (recargo 10%)",
            emision="31-08-2026", unidades=116, deptos=94, locales=1, cocheras=21, empleados=2)

json.dump(dict(meta=meta, gastos=gastos, units=units, evolucion=evolucion, estado_fin=estado_fin, composicion=composicion,
               patrimonial=patrimonial, sueldos=sueldos, proveedores=proveedores, gastos_jul=gastos_jul, estado_fin_jul=estado_fin_jul, composicion_jul=composicion_jul, patrimonial_jul=patrimonial_jul, deudores_jul=deudores_jul, ref_sep25=ref_sep25, obras=obras),
          open(DATOS + "data.json", "w"), ensure_ascii=False, indent=1, default=str)
print("OK", len(gastos), "gastos,", len(units), "unidades")
