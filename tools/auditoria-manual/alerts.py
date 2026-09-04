# Catálogo de problemas detectados - liquidaciones Julio y Agosto 2026 - Rivadavia 2069
# (severidad, área, título, evidencia, monto, recomendación)
ALERTS = [
 ("CRÍTICO","Control interno / caja",
  "La administración maneja millones en efectivo: cobra en efectivo, no deposita y paga proveedores grandes en efectivo con recibos manuscritos",
  "Agosto: caja cierra con $1.315.282 (68% de las disponibilidades; banco $626.104); se cobraron $1.343.706 en efectivo y no se depositaron. "
  "Julio: se pagaron $6.730.602 en efectivo. Los comprobantes de Redconar muestran que la cooperativa de seguridad C.S.I. cobró $2.696.045 en efectivo contra un recibo manuscrito genérico firmado 'Pamela Ogando', sin recibo oficial; "
  "LO & CO (porcelanato) emitió recibos por $1.200.000 en efectivo y $803.457 por transferencia, pero la liquidación registra los $2.003.457 como salida de caja. "
  "En septiembre 2025 la caja tenía $4.796.002 (66% de las disponibilidades): es un patrón. La Ley 941 (CABA) exige depositar los fondos en cuenta bancaria del consorcio.",
  6730602.30,
  "Exigir depósito inmediato del efectivo, prohibir pagos en efectivo por encima de un mínimo, recibos oficiales del proveedor y conciliación de caja contra comprobantes."),
 ("CRÍTICO","Pagos a una propietaria",
  "$4.757.392 salieron del consorcio hacia la propietaria de 13-B, registrados en la liquidación a nombre de proveedores",
  "Comprobantes descargados de Redconar: (1) recibo del 23-07-2026 por $2.000.000 en efectivo firmado 'Acosta Rosana, DNI 17.839.569', sin concepto, registrado como pago a cuenta a SACZEWICZYK; "
  "(2) transferencia del 12-08-2026 por $2.552.000 a la cuenta de Banco Nación de Acosta Hermelinda Rosana (CUIT 27-17839569-1), registrada como 'saldo factura 7' de SACZEWICZYK; "
  "(3) transferencia del 12-08-2026 por $205.392 a la misma cuenta, registrada como LEV RENTAL SRL (factura B a nombre de Acosta como consumidor final). "
  "La factura N° 7 de Saczewiczyk ($4.552.000) está emitida al consorcio, pero ninguno de los dos pagos fue a la cuenta de Saczewiczyk (CUIT 27-27086831-8). Solo la factura 8 ($700.000, pintura) no tiene comprobante de pago.",
  4757392.00,
  "Exigir explicación escrita: por qué el dinero fue a la propietaria y no a los proveedores, quién autorizó cada pago y con qué respaldo. Pedir recibos oficiales de Saczewiczyk por los $4.552.000."),
 ("CRÍTICO","Liquidez",
  "El consorcio quemó $11 M de reservas en julio y hoy no cubre las facturas pendientes",
  "Disponibilidades: $12.000.224 (fin junio) → $923.627 (fin julio) → $1.941.386 (fin agosto). Facturas pendientes $4.806.667 (Peñaloza: 2 cuotas de $2.333.333 + $140.000 sin identificar). Déficit de $2.865.280. "
  "En julio se gastaron $32,5 M y se cobraron $21,5 M.",
  -2865280.36,
  "Proyectar flujo de caja de septiembre-octubre y definir si las cuotas de obra se cubren con una expensa extraordinaria explícita."),
 ("CRÍTICO","Obras / contratación",
  "$20,4 M en dos meses (33% del gasto) fueron obras dentro de unidades privadas, liquidadas como expensas ordinarias",
  "Julio $10.203.457 + agosto $7.585.333 en 'Mantenimientos en unidades', más $5.300.000 de serpentinas (Roth) cargados en 'Abonos y servicios'. "
  "Solo 13-B (ACOSTA) concentra $12.155.457: porcelanato material $2.003.457 + colocación $4.552.000 + pintura $700.000 + serpentina $4.900.000. "
  "Programa de calefacción total ≈ $27,2 M (Peñaloza $14 M + Roth $7,95 M + reposición 13-B $5,25 M). No se cita acta de asamblea, presupuestos comparativos ni denuncia del siniestro a Allianz (cobertura daños por agua $5 M).",
  20388790.34,
  "Solicitar acta de asamblea que aprueba las obras, presupuestos comparativos, informe técnico que justifique la responsabilidad del consorcio y denuncia del siniestro a la aseguradora."),
 ("ALTO","Prorrateo",
  "La misma obra se prorrateó con criterios distintos en julio y agosto; se cobra $1,83 M más que el gasto sin concepto",
  "Anticipo Peñaloza de julio ($5 M) fue a columna A (las cocheras pagaron); la cuota de agosto ($4,33 M) fue a columna D (cocheras exentas). Certificación Roth y Metrogas secundaria cambian de A a D entre meses. "
  "Agosto: importe a cobrar $31.705.961 vs. gastos $29.876.923 (+$1.829.037, todo en columna A). No se informa fondo de reserva ni su saldo. En 6 meses: prorrateado $150,8 M, gastado $142,7 M, cobrado $141,7 M.",
  1829037.44,
  "Exigir criterio de prorrateo estable por obra y que todo excedente se identifique como fondo de reserva o expensa extraordinaria con saldo informado."),
 ("ALTO","Morosidad",
  "Deuda concentrada y crónica: UC-1 (DEL VALLE) debe 12,5 meses y no hay gestión de cobro visible",
  "UC-1 pasó de $1.193.442 (julio) a $1.425.249 (agosto): 35% de la deuda total sobre una expensa de $114.072/mes. SARFIEL (8-D) $546.015 → $829.879 (3,4 meses). CONTRERAS (4-B) $251.728 → $644.682. "
  "Seis unidades aparecen como deudoras en ambos meses. Cuatro no pagaron nada en agosto. Los honorarios legales de julio y agosto ($387.900) no incluyen ninguna acción de cobro.",
  4027770.23,
  "Pedir estado de intimaciones y juicios por unidad. Iniciar carta documento y ejecución para UC-1, 8-D y 4-B."),
 ("ALTO","Contingencias legales",
  "El consorcio pagó la defensa de la administración en una denuncia por violación de la Ley 941, y hubo un pago por error de $1.350.000 al abogado",
  "Factura N° 262 de Navarro Fernández (03-07-2026, $200.000): 'patrocinio letrado audiencia por denuncia ante el Registro Público de Administradores de Consorcio por violación de la Ley 941'. Esa denuncia es contra la administración, no contra el consorcio. "
  "Agosto: contestación de carta documento ($135.000) y mediación con UF 68 ($29.000), sin explicar el reclamo. Julio: carta documento a PB-E ($23.900). "
  "El 09-08 la administración transfirió $1.350.000 al abogado por la factura de $135.000; él devolvió $1.215.000 el 10-08 ('devolución por error'). Ni el error ni la devolución figuran en la liquidación.",
  1350000.00,
  "Pedir informe del asesor legal (partes, objeto, estado, contingencia) y definir en asamblea si corresponde que el consorcio pague la defensa de la administradora. Exigir doble control en las transferencias."),
 ("ALTO","Obras / contratación",
  "Proveedor nuevo (facturas N° 7 y 8) ejecuta $5,25 M; factura del 31-08 pagada el mismo día; factura de Peñaloza emitida después del pago",
  "SACZEWICZYK: factura 00001-00000007 ($4.552.000) y 00001-00000008 ($700.000), sin dirección informada, $2 M cobrados en efectivo. "
  "PEÑALOZA: factura 00003-00000201 fechada 24-07 pagada el 13-07. KEVIN LUCAS AVALOS (factura N° 5) cobra $70.000 en efectivo.",
  5252000.00,
  "Verificar inscripción ARCA y antecedentes; exigir factura antes del pago y presupuestos comparativos."),
 ("ALTO","Obras / contratación",
  "Conflicto de interés: quien certifica los equipos térmicos es quien factura las reparaciones",
  "MARIO LEONARDO ROTH cobra $90.000/mes por certificar equipos térmicos y ejecutó las serpentinas por $7.950.000 (3 cuotas: junio, julio y agosto, hoy totalmente pagas).",
  7950000.00,
  "Separar roles: certificación por un tercero independiente; presupuestos alternativos para reparaciones."),
 ("ALTO","Gasto ajeno al consorcio",
  "El 'servicio de internet de cámaras' es la factura personal de Flow del encargado, pagada como haberes",
  "Las facturas de Cablevisión/Flow de julio y agosto están a nombre de RAMON GONZALEZ, Av. Rivadavia 2069 1 D, e incluyen 'Internet 100 MB + Flow Full con Deco' y una línea móvil. "
  "El consorcio paga cada mes el renglón de internet+Flow ($78.966 en julio, $80.440 en agosto) con una transferencia al encargado bajo el motivo 'acreditamiento de haberes'. El servicio no está contratado por el consorcio.",
  159406.40,
  "Contratar el servicio de internet para cámaras a nombre del consorcio y dejar de pagar la factura personal del encargado."),
 ("MEDIO","Pagos a terceros distintos del emisor",
  "Facturas pagadas a cuentas de personas o empresas distintas de quien facturó",
  "MATHIL (Metalúrgica Larraude, CUIT 30-70738288-7): las dos facturas de $75.000 (nov y dic 2025) se transfirieron a Soluciones en Extinguidores S.R.L. (CUIT 30-71903002-1). "
  "LOPEZ RAMIREZ VIDAL (CUIT 20-94541540-2, lijado 12-B): los $200.000 se transfirieron a Gustavo David Lopez Mareco (CUIT 20-37992492-2).",
  350000.00,
  "Exigir que los pagos vayan a la cuenta bancaria del emisor de la factura, o una autorización escrita del emisor cuando se pague a un tercero."),
 ("MEDIO","Respaldo documental",
  "Gastos sin comprobante de pago o con comprobantes reutilizados",
  "Roth, cuota del 21-08 ($2.650.000): los adjuntos son las transferencias del 29-05 y del 13-07 (cuotas 1 y 2); no hay comprobante de un tercer pago. "
  "Peñaloza, anticipo de $5.000.000 (julio): solo la factura, sin comprobante de pago. Avalos $70.000 en efectivo sin recibo. Saczewiczyk factura 8 ($700.000) sin pago adjunto. "
  "Sin ningún adjunto en dos meses: Allianz (4 cuotas + endoso), Berkley, Banco Galicia y los honorarios de administración de julio ($806.980). 15 líneas de gasto sin respaldo alguno.",
  8420000.00,
  "Pedir los comprobantes faltantes y verificar en el resumen bancario que la cuota 3 de Roth se haya pagado una sola vez."),
 ("ALTO","Consistencia contable",
  "Facturas pendientes arrastran $140.000 sin identificar en ambos meses",
  "Julio: $5.342.000 = Saczewiczyk $2.552.000 + Roth $2.650.000 + $140.000. Agosto: $4.806.667 = Peñaloza $4.666.667 + $140.000. El importe no corresponde a ninguna factura informada.",
  140000.00,
  "Pedir detalle de facturas pendientes por proveedor y número."),
 ("MEDIO","Pagos atrasados / duplicación",
  "Cargas sociales se pagan sistemáticamente un mes tarde y se pagan facturas de hasta 9 meses",
  "F.931 de mayo pagado 15-07 y F.931 de junio pagado 10-08 (vencen el mes siguiente): intereses resarcitorios probables. Retenciones SIRE también con un mes de atraso. "
  "MATHIL noviembre y diciembre 2025 pagados el 09-08-2026 (275 y 251 días); SOLVER factura 31-03 pagada 04-08 (126 días).",
  2176471.27,
  "Verificar que Mathil nov/dic 2025 no se hayan liquidado antes (riesgo de doble pago) y cuantificar intereses por F.931 tardíos."),
 ("MEDIO","Costos",
  "Costos fijos suben por encima del mes anterior y los gastos bancarios llegan a $452.337",
  "Julio → agosto: honorarios administración $711.980 → $775.799 (+9,0%); gastos bancarios $394.546 → $452.337 (+14,6%); seguridad C.S.I. $2.952.305 → $3.166.032 (+7,2%); destapaciones +7,0%; Redconar +6,0%. "
  "Escaneo de documentación (Disp. 856) se cobra todos los meses ($95.000 y $99.000): ≈ $1,2 M/año aparte de los honorarios. Impuesto a débitos/créditos estimado ≈ $356.000; el resto (~$96.000) serían comisiones.",
  452336.93,
  "Pedir resumen bancario, renegociar comisiones y cuestionar el cargo mensual por escaneo."),
 ("MEDIO","Morosidad",
  "Criterio de intereses a deudores no uniforme",
  "Sobre la deuda: 10% (ASOCARG, CARRIZO, BERHO, CATTANEO), 9,6% (CONTRERAS), 8,8% (SARFIEL), 7,2% (DEL VALLE: el mayor deudor paga la menor tasa), SINGLAR 25,6% sobre la deuda remanente. El recargo del 5% por pago fuera de término sí es consistente.",
  535506.21,
  "Solicitar la fórmula de cálculo de intereses y su respaldo en el reglamento."),
 ("MEDIO","Costos / personal",
  "Horas extras recurrentes y adicionales sin concepto",
  "Encargado: 23 hs extra al 50% = $318.838/mes (14% de su bruto). Ambos empleados cobran 'Adicional' de $55.000 sin detalle. Sueldos informados a Berkley ($1.810.000 / $1.300.000) no coinciden con los recibos. Julio incluyó SAC: sueldos y cargas $9,34 M. Los comprobantes muestran adelantos de sueldo no informados en la liquidación: en julio se descontaron $350.001 (Heres) y $375.001 (Gonzales, '50% cuota por adelantos') y el 23-07 se giró un 'a cuenta' de $50.000.",
  428837.96,
  "Revisar necesidad de horas extras, documentar el adicional y actualizar sumas aseguradas."),
 ("MEDIO","Seguros",
  "Endoso 2 de Allianz cuesta más que la póliza base y hubo un endoso 5 en julio",
  "Endoso 2: RC ampliada a $650,1 M, cuota $382.377 × 6 = $2,29 M (póliza base $268.652 × 10). Endoso 5 (julio) $39.136 por cristales.",
  382377.00,
  "Pedir justificación de los endosos y cotización alternativa."),
 ("MEDIO","Clasificación",
  "Rubros mal clasificados",
  "Retención SIRE del servicio de seguridad ($256.260) incluida en 'Sueldos y cargas sociales'. Serpentinas Roth ($7,95 M) en 'Abonos y servicios' en vez de 'Mantenimientos en unidades'. 'Servicios públicos' aparece como dos rubros. C.S.I. factura 'mes de julio' con período 'junio'.",
  256260.11,
  "Reclasificar para que el resumen por rubro refleje el destino real del gasto."),
 ("BAJO","Calidad de datos",
  "Datos incompletos o inconsistentes en el padrón",
  "Nombres truncados (CONTRERAS, / SINGLAR, / DEL, VALLE / SEGUROS EVOLUTIOÇN). Proveedores sin CUIT o dirección (Berkley, Navarro, Saczewiczyk, Roth). Pago sin identificar reiterado en ambos meses. Metrogas: julio informa el mismo número de cliente en las dos cuentas. La factura de Avalos trae la leyenda de ARCA 'la CUIT 33-60039145-9 se encuentra inactiva en los padrones y/o no inscripta en la condición seleccionada ante el IVA': verificar la situación fiscal del consorcio.",
  0,
  "Depurar padrón y detalle de proveedores; identificar los pagos con los centavos por unidad."),
]
SEV_ORDER = {"CRÍTICO":0,"ALTO":1,"MEDIO":2,"BAJO":3}

# Bullets rápidos: dónde se aplicaron los gastos mayores (julio + agosto = $62.420.048)
BULLETS = [
 ("Calefacción del edificio y unidades afectadas", 14813333.33, "Peñaloza columna sector F ($5 M jul + $4,33 M ago) y serpentinas Roth 12-B/13-B ($2,65 M + $2,65 M) + certificación ($180.000). Quedan $4,67 M por pagar."),
 ("Sueldos y cargas sociales (2 empleados)", 14773983.62, "Julio $9,08 M (incluye aguinaldo) + agosto $5,69 M, sin las retenciones de seguridad que la liquidación mezcla en este rubro. Encargado con 23 hs extra/mes."),
 ("Reposición del departamento 13-B (ACOSTA)", 7255457.01, "Porcelanato material $2 M (efectivo) + colocación $4,55 M ($2 M en efectivo) + pintura $700.000. Sumando su serpentina, 13-B recibió $12,2 M. Según los comprobantes, $4,76 M de esos pagos fueron directamente a la propietaria (efectivo y transferencias)."),
 ("Seguridad privada (Cooperativa C.S.I.)", 6098657.89, "Junio $2,95 M (pagado en efectivo) y julio $3,17 M, incluidas retenciones. Es el proveedor recurrente más caro."),
 ("Gas y calefacción central (Metrogas)", 3938952.69, "Agosto $3,48 M (1/2 del bimestre de invierno) + julio $0,41 M. El bimestre 04/2025 costó $2,63 M: +32% interanual."),
 ("Electricidad (Edesur)", 3303066.04, "Julio $1,84 M (dos medidores) + agosto $1,47 M."),
 ("Administración (honorarios + escaneo)", 1681779.00, "Julio $806.980 + agosto $874.799. El escaneo (Disp. 856) se cobra todos los meses."),
 ("Seguros (Allianz + Berkley)", 1436873.57, "Póliza base + 3 endosos + vida colectivo. El endoso 2 ($382.377/mes) cuesta más que la póliza base."),
 ("Otras obras en unidades (12-B, 14-E, 14-F)", 1200000.00, "Saldo lijado 12-B $200.000, columna de agua 14-E/14-F $680.000, venecitas 14-F $320.000 (más $605.000 puerta ascensor 4)."),
 ("Gastos bancarios", 846882.76, "Julio $394.546 + agosto $452.337 (+14,6%)."),
 ("Abogado (Navarro Fernández) y cartas documento", 387900.00, "Denuncia en Defensa del Consumidor, contestación de carta documento, mediación UF 68, carta documento PB-E."),
]

# Hallazgos por comprobante (verificación en Redconar, 150 adjuntos de julio y agosto 2026)
DOC_FINDINGS = [
 ("2026-07","23-07-2026","SACZEWICZYK MARIA EUGENIA",2000000.00,"Recibo manuscrito (FC N° 0007 MARIA RECIBO)","Recibo por $2.000.000 en efectivo firmado 'Acosta Rosana, DNI 17.839.569', sin concepto. El dinero lo recibió la propietaria de 13-B, no la proveedora.","CRÍTICO"),
 ("2026-08","12-08-2026","SACZEWICZYK MARIA EUGENIA",2552000.00,"Office Banking 'SALDO POR FC N°7'","Transferencia a Acosta Hermelinda Rosana (CUIT 27-17839569-1), Banco Nación. La factura 7 la emitió Saczewiczyk (CUIT 27-27086831-8) al consorcio.","CRÍTICO"),
 ("2026-08","12-08-2026","LEV RENTAL SRL / H. R. ACOSTA",205392.00,"Factura B 0021-00028257 + ticket de pago","Factura a nombre de Hermelinda Rosana Acosta como consumidor final (MercadoPago); el consorcio le transfirió el importe a su cuenta.","CRÍTICO"),
 ("2026-07","29-07-2026","COOPERATIVA DE TRABAJO C.S.I.",2696045.29,"Recibo manuscrito genérico","$2.696.045 en efectivo contra un recibo de librería firmado 'Pamela Ogando', sin recibo oficial de la cooperativa (responsable inscripto).","CRÍTICO"),
 ("2026-07","11-07-2026","LO & CO S.A. (Permat)",2003457.01,"Factura B + 2 recibos","Recibos: $1.200.000,01 'efectivo - Fast Pay c/entrega mercadería' y $803.457 'transferencia bancaria'. La liquidación registra los $2.003.457 como pago en efectivo de caja.","ALTO"),
 ("2026-08","09-08-2026","NAVARRO FERNANDEZ RICARDO ESTEBAN",1350000.00,"Transferencia + crédito 'devolución por error'","Se transfirieron $1.350.000 por una factura de $135.000; el abogado devolvió $1.215.000 al día siguiente. No consta en la liquidación.","ALTO"),
 ("2026-07","03-07-2026","NAVARRO FERNANDEZ RICARDO ESTEBAN",200000.00,"Factura C 00003-00000262","'Patrocinio letrado audiencia por denuncia ante el Registro Público de Administradores por violación de la Ley 941': el consorcio pagó la defensa de la administración.","ALTO"),
 ("2026-08","10-08-2026","CABLEVISION S.A. (Flow)",80440.21,"Factura Flow + transferencia","Factura a nombre de Ramón Gonzalez (encargado), Rivadavia 2069 1 D, con Flow Full + Deco y línea móvil. Pagado al encargado como 'acreditamiento de haberes'. Igual en julio ($78.966).","ALTO"),
 ("2026-08","09-08-2026","MATHIL (Metalúrgica Larraude)",150000.00,"2 facturas B + 2 transferencias","Facturas de Metalúrgica Larraude (CUIT 30-70738288-7) pagadas a Soluciones en Extinguidores S.R.L. (CUIT 30-71903002-1).","MEDIO"),
 ("2026-07","01-07-2026","LOPEZ RAMIREZ VIDAL",200000.00,"Factura C + transferencia","Factura de Lopez Ramirez Vidal (CUIT 20-94541540-2) pagada a Gustavo David Lopez Mareco (CUIT 20-37992492-2).","MEDIO"),
 ("2026-08","21-08-2026","MARIO LEONARDO ROTH",2650000.00,"Adjuntos de la cuota 3","Los comprobantes adjuntos son las transferencias del 29-05-2026 y del 13-07-2026 (cuotas 1 y 2). No hay comprobante de un pago el 21-08.","MEDIO"),
 ("2026-07","13-07-2026","PEÑALOZA ALEJANDRO ROBERTO",5000000.00,"Factura C 00003-00000201","Factura fechada 24-07 por un pago del 13-07. Sin comprobante de pago adjunto.","MEDIO"),
 ("2026-08","01-08-2026","KEVIN LUCAS AVALOS",70000.00,"Factura C 00001-00000005","Pagado en efectivo sin recibo. La factura trae la leyenda de ARCA: CUIT del consorcio inactiva / no inscripta en la condición seleccionada.","BAJO"),
 ("2026-07","01-07-2026","Sueldos (Heres / Gonzales)",725001.40,"Transferencias de haberes","Se transfirió $2.020.331 (neto $2.370.332) y $2.375.536 (neto $2.750.537): descuento de adelantos de sueldo que no aparecen en la liquidación. A cuenta de $50.000 el 23-07.","BAJO"),
 ("ambos","","Allianz, Berkley, Banco Galicia, Crocamo (julio), FATERYH (julio)",2340000.00,"Sin adjuntos","15 líneas de gasto sin ningún comprobante adjunto en Redconar.","MEDIO"),
]
