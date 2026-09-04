# Contenido de la asamblea extraordinaria del 3/09/2026 - Rivadavia 2067/69/71
AGENDA = [
 dict(id="1", titulo="Designación de presidente, secretario y dos firmantes del acta",
      decidir="Elegir quién preside, quién toma el acta y dos propietarios que la rubrican.",
      guia="Conviene que presida un propietario y no la administración. Anotar nombres y unidades para el acta.", mocion=None),
 dict(id="2", titulo="Validez de la asamblea",
      decidir="Constatar quórum: presentes más poderes, en unidades y en porcentual, sobre el total de 116 unidades y 99,91 %.",
      guia="Con 50 % + 1 del total (59 unidades y más de 49,96 %) las decisiones son firmes. Si no, lo votado queda como proposición y se circula 15 días (art. 2060 CCyC). La app lo calcula en la pestaña Votar.", mocion=None),
 dict(id="3", titulo="Los 70 años del encargado Ramón Gonzalez: camino a seguir",
      decidir="Definir si el encargado continúa en funciones o se inicia el proceso de desvinculación con la jubilación.",
      guia="Pedir a la administración el costo de cada alternativa: indemnización según CCT 589/10 y antigüedad (12 años), plazo de intimación a jubilarse, y costo de reemplazo. El recibo de julio muestra 23 horas extra al 50 % ($318.838) y un 'adicional' de $55.000 sin concepto.",
      mocion="Que Ramón Gonzalez continúe como encargado"),
 dict(id="4", titulo="Situación conflictiva con los habitantes del departamento 10-E",
      decidir="Es un punto informativo: la administración informa. Si se propone alguna acción, se vota como moción aparte.",
      guia="Según los comprobantes, en agosto se pagó un anticipo de mediación con el propietario de la UF 68 (10-E) por $29.000 y una contestación de carta documento por $135.000. La unidad está al día con las expensas. Pedir: quién reclama, qué reclama, en qué instancia está y qué costo estimado tiene para el consorcio.", mocion=None),
 dict(id="5", titulo="Reglamento interno con régimen de multas: análisis y aprobación",
      decidir="Aprobar o no el reglamento interno con multas para que sea obligatorio dentro del consorcio.",
      guia="Un reglamento interno con multas necesita mayoría de la asamblea y no puede contradecir el reglamento de copropiedad ni el CCyC (art. 2056 y sig.). Conviene votar el texto completo tal cual se circuló; si hay cambios, anotarlos artículo por artículo antes de votar.",
      mocion="Aprobar el reglamento interno con régimen de multas"),
 dict(id="6", titulo="Constitución de un tribunal para el análisis y aplicación de las multas",
      decidir="Crear o no un tribunal de propietarios que analice y aplique las multas, y quiénes lo integran.",
      guia="Definir cantidad de miembros, cómo se eligen, duración del mandato y cómo se apela una multa. Si se aprueba, elegir los integrantes en el acto y dejar constancia en el acta.",
      mocion="Constituir el tribunal de multas"),
]

# Preguntas a la administración, en tono factual, con el documento que las respalda (los comprobantes están en Redconar > Mi cuenta > Gastos y comprobantes)
PREGUNTAS = [
 dict(id="q1", tema="Pagos a una propietaria", pregunta="El 23-07 se pagaron $2.000.000 en efectivo 'a cuenta' de la factura 7 de Saczewiczyk (porcelanato 13-B) y el recibo está firmado por Rosana Acosta, DNI 17.839.569, propietaria de 13-B. El 12-08 el 'saldo' de $2.552.000 se transfirió a la cuenta de Banco Nación de Acosta Hermelinda Rosana. ¿Por qué los pagos fueron a la propietaria y no a la proveedora que emitió la factura?",
      doc="Redconar, gastos de julio (23-07) y agosto (12-08): recibo 'FC N° 0007 MARIA RECIBO' y transferencia 'SALDO POR FC N°7'.", monto=4552000),
 dict(id="q2", tema="Pagos a una propietaria", pregunta="La bomba sumergible de $205.392 se facturó a nombre de Hermelinda Rosana Acosta como consumidor final (factura B de LEV Rental) y el consorcio le transfirió el importe a ella. ¿Quién autorizó que una propietaria comprara equipamiento de partes comunes y por qué no se facturó al consorcio?",
      doc="Redconar, gasto del 12-08-2026: factura 0021-00028257 y ticket de transferencia.", monto=205392),
 dict(id="q3", tema="Obras en unidades", pregunta="Entre julio y agosto se pagaron $12,2 millones en trabajos dentro del departamento 13-B (porcelanato, colocación, pintura y serpentina) y $3,3 millones en 12-B, como expensas ordinarias. ¿Qué acta de asamblea aprobó esas obras, qué presupuestos comparativos hubo y se denunció el siniestro a Allianz (cobertura de daños por agua de $5.000.000)?",
      doc="Liquidaciones de julio y agosto 2026, rubro 'Mantenimientos en unidades' y facturas de Roth 4182/4191.", monto=15455457),
 dict(id="q4", tema="Manejo de efectivo", pregunta="En julio se pagaron $6.730.602 en efectivo, incluidos $2.696.045 a la cooperativa de seguridad contra un recibo manuscrito de librería firmado 'Pamela Ogando'. Al 31-08 la caja en efectivo tiene $1.315.282, el 68 % de la liquidez del consorcio. ¿Por qué no se depositan los fondos en la cuenta del consorcio, como exige la Ley 941?",
      doc="Liquidación de agosto, 'Composición de estado financiero'; Redconar, gasto del 29-07 'F C N° 4833 06-2026 RECIBO'.", monto=6730602),
 dict(id="q5", tema="Liquidez", pregunta="Las disponibilidades pasaron de $12.000.224 a fin de junio a $923.627 a fin de julio. Con $1.941.386 al 31-08 y facturas pendientes por $4.806.667 (dos cuotas de Peñaloza), ¿cómo se van a pagar las cuotas de septiembre y octubre? ¿Habrá expensa extraordinaria?",
      doc="Liquidaciones de julio y agosto, 'Estado financiero' y 'Estado patrimonial'.", monto=4806667),
 dict(id="q6", tema="Honorarios legales", pregunta="La factura 262 de Navarro Fernández ($200.000, julio) es por 'patrocinio letrado en audiencia por denuncia ante el Registro Público de Administradores por violación de la Ley 941'. ¿Por qué el consorcio pagó la defensa de la administración en una denuncia contra la administración? ¿Quién la presentó y en qué estado está?",
      doc="Redconar, gasto del 03-07-2026: factura 00003-00000262.", monto=200000),
 dict(id="q7", tema="Control de pagos", pregunta="El 09-08 se transfirieron $1.350.000 al abogado por una factura de $135.000; al día siguiente devolvió $1.215.000 'por error'. Ni el error ni la devolución aparecen en la liquidación. ¿Qué control hay antes de cada transferencia?",
      doc="Redconar, gasto del 10-08-2026: transferencia 'FC N° 0268 NAVARRO Pago' y crédito 'DEVOLUCION NAVARRO POR ERROR'.", monto=1350000),
 dict(id="q8", tema="Gasto ajeno al consorcio", pregunta="El 'servicio de internet de cámaras' ($80.440 en agosto, $78.966 en julio) es la factura personal de Flow del encargado, a nombre de Ramón Gonzalez, con Flow Full, decodificador y línea móvil, pagada como 'acreditamiento de haberes'. ¿Desde cuándo se paga y por qué el servicio no está contratado a nombre del consorcio?",
      doc="Redconar, gastos del 02-07 y 10-08-2026: 'FC N° 04960-… INTERNET' y comprobante de pago.", monto=159406),
 dict(id="q9", tema="Prorrateo", pregunta="El anticipo de Peñaloza de julio ($5.000.000) se prorrateó en la columna A (las cocheras pagaron) y la cuota de agosto ($4.333.333) en la columna D (cocheras exentas). En agosto se prorratearon $1.829.037 más que el gasto del mes sin concepto. ¿Cuál es el criterio y dónde está ese excedente?",
      doc="Liquidaciones de julio y agosto, 'Estado de cuentas y prorrateo'.", monto=1829037),
 dict(id="q10", tema="Morosidad", pregunta="La cochera UC-1 debe $1.425.249, equivalente a 12,5 meses de expensas; 8-D debe 3,4 meses y 4-B 1,7 meses. Los honorarios legales de julio y agosto no incluyen ninguna acción de cobro. ¿Qué intimaciones o juicios se iniciaron?",
      doc="Liquidación de agosto, 'Propietarios con saldo deudor'.", monto=4027770),
 dict(id="q11", tema="Pagos a terceros", pregunta="Las facturas de Mathil (noviembre y diciembre 2025, $150.000) se transfirieron a Soluciones en Extinguidores S.R.L., y la de Lopez Ramirez Vidal ($200.000) a Gustavo David Lopez Mareco. ¿Por qué se paga a una cuenta distinta de la de quien factura?",
      doc="Redconar, gastos del 09-08 (Mathil) y 01-07-2026 (Lopez Ramirez): comprobantes de pago.", monto=350000),
 dict(id="q12", tema="Respaldo documental", pregunta="La cuota de Roth del 21-08 ($2.650.000) tiene como comprobantes las transferencias del 29-05 y del 13-07 (cuotas anteriores); el anticipo de Peñaloza de julio ($5.000.000) no tiene comprobante de pago; y 15 líneas de gasto (Allianz, Berkley, Galicia, honorarios de julio) no tienen ningún adjunto. ¿Se pueden presentar hoy esos comprobantes?",
      doc="Redconar, gastos del 21-08 (Roth) y 13-07 (Peñaloza); líneas sin adjuntos en julio y agosto.", monto=8420000),
 dict(id="q13", tema="Conflicto de interés", pregunta="Mario Leonardo Roth cobra $90.000 por mes por certificar los equipos térmicos y a la vez ejecutó las reparaciones de serpentinas por $7.950.000. ¿Se pidieron presupuestos a otros instaladores?",
      doc="Liquidaciones de julio y agosto: facturas 4331/4417 (certificación) y 4182/4183/4191 (obras).", monto=7950000),
 dict(id="q14", tema="Personal", pregunta="En julio se descontaron de los sueldos $350.001 (Heres) y $375.001 (Gonzalez) por 'adelantos', que no figuran en ninguna liquidación, y el encargado cobra 23 horas extra al 50 % cada mes. ¿Quién autoriza los adelantos y las horas extra?",
      doc="Redconar, gastos del 01-07-2026: comprobantes 'Pago de recibo… menos descuento de adelantos'.", monto=725001),
]

CONVOCATORIA = """Administración Almazare, RPA 5911. Ciudad de Buenos Aires, 25 de agosto de 2026.
Asamblea extraordinaria del Consorcio de Propietarios Rivadavia 2067/69/71, el 3/09/2026 a las 19:00 en la planta baja del edificio. Finalización prevista: 20:30.

Orden del día
1. Designación de presidente y secretario de la asamblea y 2 personas para rubricar el acta.
2. Validez de la asamblea.
3. Cumplimiento de los 70 años del encargado Ramón y decisión de los propietarios del camino a seguir.
4. Situación conflictiva con los habitantes del depto 10-E. Información al consorcio.
5. Análisis del reglamento interno con el agregado de multas para las transgresiones a sus artículos. Aprobación del mismo en la asamblea para que tenga fuerza de ley dentro del consorcio.
6. Constitución de un tribunal dedicado únicamente al análisis y aplicación de las multas.

Nota de la convocatoria: de no reunirse el 50 % + 1 de la totalidad de los propietarios, las decisiones que tomen en mayoría los presentes se consideran "proposiciones", que quedan convalidadas si no reciben objeciones en contrario de los propietarios ausentes, en suficiente mayoría, luego de circularizarlas por escrito o por Redconar. Transcurridos 15 días quedan firmes (art. 2060 CCyC).
Quien no pueda asistir puede hacerse representar con el poder adjunto, previa firma en el libro de firmas de la administración."""

PODER = """PODER
En mi carácter de propietario de la unidad N° ______ del Consorcio de Propietarios del edificio de la calle Rivadavia 2067/69/71 de Capital Federal, autorizo a ______________________________, DNI N° ______________, a representarme en la asamblea extraordinaria que se celebrará el día 3 de septiembre de 2026 a las 19:00 horas, facultándolo al efecto para que en mi nombre y representación intervenga en las deliberaciones, votando y decidiendo cuando fuera necesario.
Buenos Aires, 3 de septiembre de 2026.            Firma: ______________________"""
