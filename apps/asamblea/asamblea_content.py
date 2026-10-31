# Contenido de la asamblea - Rivadavia 2067/69/71
# Asamblea ordinaria (rendición de cuentas del ejercicio octubre 2025 - octubre 2026).
# Convocatoria de la administración Almazare recibida el 30/10/2026; asamblea el 17/11/2026.
ASAMBLEA = dict(
    titulo="Asamblea ordinaria",
    fecha="2026-11-17",        # ISO; la UI la formatea en es-AR
    hora="19:00",
    nota="Cierre previsto 21:00. Si no podés asistir, dejá la carta poder (está en Documentos → Convocatoria y poder; requiere firma previa en el libro de la administración).",
    notificacion=None,          # fecha ISO de notificación a los ausentes (plazo art. 2060). None = se estima 15 días desde la asamblea.
)

AGENDA = [
 dict(id="1", titulo="Designación de presidente, secretario y dos firmantes del acta",
      decidir="Elegir quién preside la asamblea, quién toma el acta y dos propietarios que la rubrican.",
      guia="Conviene que presida un propietario y no la administración. Anotar nombres y unidades para el acta.", mocion=None),
 dict(id="2", titulo="Validez de la asamblea",
      decidir="Constatar quórum: presentes más poderes, en unidades y en porcentual, sobre el total de 116 unidades y 99,91 %.",
      guia="Con 50 % + 1 del total (59 unidades y más de 49,96 %) las decisiones son firmes. Si no, lo votado queda como proposición y se circula 15 días (art. 2060 CCyC). La app lo calcula en la pestaña Votar.", mocion=None),
 dict(id="3", titulo="Aprobación del ejercicio octubre 2025 – octubre 2026",
      decidir="Aprobar o no la rendición de cuentas del ejercicio completo. Aprobarla implica dar por buenas las cuentas del año; lo razonable es aprobar solo lo que esté aclarado y dejar asentado en el acta qué queda pendiente de respuesta.",
      guia="Dato a favor: los estados enviados el 30/10 coinciden al centavo, mes a mes, con las nueve liquidaciones auditadas de forma independiente (enero a septiembre). Las preguntas no son sobre el cuadre global sino sobre gastos puntuales. Antes de votar conviene pedir aclaración de los puntos abiertos (el detalle con montos y comprobantes está en la pestaña Preguntas y en Documentos → Expensas): la factura 183 de Peñaloza por $2,8M liquidada en febrero y también en marzo; la obra de calefacción y pisos de 12-B y 13-B ($18,5M en 13 facturas de 7 proveedores, con pagos que no fueron al emisor de la factura); el criterio para pagar con expensas trabajos dentro de unidades privadas; la caja, que cierra el ejercicio con $1,85M (menos del 6 % de un mes de gastos); y la liquidación de octubre, que todavía no se vio ($32,2M, con sueldos por $10,1M). Si algo no se responde en la asamblea, pedir que conste en acta el compromiso de responder por escrito con plazo.",
      mocion="Aprobar la rendición de cuentas del ejercicio octubre 2025 – octubre 2026"),
 dict(id="4", titulo="Ratificación o rectificación de la administración actual",
      decidir="Ratificar a la administración Almazare o designar otra. La decisión razonable depende de cómo se resuelva el punto 3.",
      guia="Pedir antes de votar: informe de gestión del ejercicio, honorarios actuales y su evolución (subieron 7,5 % en un mes en febrero), y compromiso de prácticas concretas: comprobante adjunto para todo gasto, pago directo al proveedor que factura (sin cuentas intermedias), dos o más presupuestos para obras grandes y registro del medio de pago real. Si la asamblea ratifica, puede hacerlo dejando asentadas esas condiciones en el acta.",
      mocion="Ratificar a la administración actual"),
 dict(id="5", titulo="Ratificación o rectificación del Consejo de Propietarios",
      decidir="Ratificar el consejo actual o renovarlo total o parcialmente.",
      guia="El consejo es el control de cercanía de la administración (art. 2064 CCyC): revisa cuentas y acompaña decisiones. Preguntar quiénes lo integran hoy, si están dispuestos a seguir y si hay vecinos nuevos que quieran sumarse. Conviene que quede integrado por propietarios de distintos cuerpos del edificio.",
      mocion="Ratificar al Consejo de Propietarios"),
 dict(id="6", titulo="Continuidad o no del conservador del ascensor — presupuestos",
      decidir="Decidir si sigue el conservador actual (Ascensores Laufken) o se cambia, comparando presupuestos.",
      guia="Laufken facturó ~$15,6M en el ejercicio: el abono mensual (que el análisis marcó por encima del tope de referencia en varios meses) más la obra del ascensor 3 (~$9,8M: anticipo 50 % en enero y 4 cuotas de $1,85M). Pedir: los presupuestos alternativos que menciona la convocatoria, qué incluye cada abono (los 3 ascensores, repuestos, emergencias), el acta de conformidad de la obra del ascensor 3 y el estado del libro de inspección. No votar sin ver al menos dos presupuestos comparables.",
      mocion="Continuar con el conservador actual de ascensores"),
 dict(id="7", titulo="Calefacción: nueva pérdida en el cuerpo A, 9º y 8º — presupuestos",
      decidir="Aprobar la reparación de la nueva pérdida y con qué presupuesto.",
      guia="Es la cuarta intervención grande de calefacción del ejercicio: columna 5B/4B/3B ($2,6M, enero), serpentinas 12-B y 13-B ($7,95M, ROTH), columna sector F pisos 8-12 ($11,67M, Peñaloza). Antes de aprobar otra reparación puntual, pedir un diagnóstico integral de la instalación: qué tramos quedan originales, cuántas pérdidas más son esperables y si conviene un plan por etapas con precio por columna. Pedir mínimo dos presupuestos con el mismo alcance por escrito (materiales, albañilería y terminación incluidas) y definir quién certifica el trabajo terminado.",
      mocion="Aprobar la reparación de la pérdida de calefacción del cuerpo A (8º y 9º)"),
 dict(id="8", titulo="Desprendimiento de mampostería — presupuestos de reparación",
      decidir="Aprobar la reparación del desprendimiento de mampostería y con qué presupuesto.",
      guia="Si hay riesgo de caída a la vía pública o a patios es un tema de seguridad y va primero en prioridades. Pedir: informe técnico de un profesional (dónde está el desprendimiento, causa, si hay riesgo inmediato), si aplica la obligación de conservación de fachadas de CABA, medidas provisorias (vallado o malla) hasta la obra, y dos o más presupuestos con el mismo alcance. Verificar que el contratista tenga seguro y ART.",
      mocion="Aprobar la reparación del desprendimiento de mampostería"),
 dict(id="9", titulo="Recursos para los trabajos y orden de prioridades",
      decidir="Definir con qué fondos se pagan las obras aprobadas (expensas extraordinarias, cuotas, fondo de reserva) y en qué orden se hacen.",
      guia="Dato del ejercicio: en julio y agosto las disponibilidades no cubrían las facturas pendientes, o sea que no hay colchón. Pedir el estado de caja actual antes de votar montos. Criterio de prioridad razonable: 1º seguridad (mampostería), 2º servicios esenciales (calefacción, ascensor), 3º el resto. Si se aprueban expensas extraordinarias, que quede claro el monto total, en cuántas cuotas y qué obra financia cada una; y aprovechar para constituir un fondo de reserva que evite esta fragilidad de caja.",
      mocion="Aprobar el esquema de recursos y el orden de prioridades"),
]

# Preguntas a la administración para la rendición de cuentas (ejercicio oct 2025 - oct 2026).
# Surgen del análisis del motor sobre las liquidaciones de enero a septiembre 2026
# (todas cuadradas al centavo). Los hechos se describen con comprobante; qué falta es
# precisamente lo que se pide. Sin conclusiones sobre personas.
PREGUNTAS = [
 dict(id="p1", tema="Posible doble liquidación", monto=2800000,
      pregunta="La factura 00003-00000183 de Peñaloza Alejandro Roberto por $2.800.000 (cambio de caños de bajada 2-D/2-E) aparece liquidada en la expensa de febrero y también en la de marzo, con el mismo comprobante. ¿Fueron dos cuotas de un trabajo de $5.600.000 o se liquidó dos veces el mismo trabajo? Si fueron cuotas, ¿pueden mostrar el presupuesto aprobado por ese total?",
      doc="Expensas de febrero y marzo 2026; factura 00003-00000183"),
 dict(id="p2", tema="Obra de calefacción y pisos en 12-B y 13-B", monto=18513799,
      pregunta="Entre mayo y septiembre la reparación de las serpentinas de calefacción de 12-B y 13-B y la reconstrucción de los pisos costó $18,5M pagados por expensas: cambio de serpentinas $7.950.000 (ROTH, facturas 4182/4191), rotura y recolocación de piso en 13-B $5.252.000 (Saczewiczyk), porcelanato $2.003.457 (LO & CO), contrapiso 13-B y cielorraso 12-B $2.600.000 (Gómez), plastificado de pisos 12-B $400.000, alquiler de equipos $205.392 y materiales $102.950. Pedimos: (1) el informe del siniestro que originó la obra y el presupuesto total aprobado antes de empezar — en las expensas el gasto aparece repartido en 13 facturas de 7 proveedores a lo largo de 5 meses, sin un presupuesto integral visible; (2) el criterio de alcance: el cambio de serpentina es instalación común, pero ¿la reposición de porcelanato de primera marca, el plastificado y la pintura interior corresponden al consorcio o al propietario?; (3) el circuito de pagos: la factura del porcelanato dice 'abonadas por dpto 13ºB', la de LEV Rental está a nombre de la propietaria del 13-B y varios pagos se transfirieron a su cuenta y no a la del proveedor que facturó — si la propietaria adelantó pagos y el consorcio le reembolsó, que se documente ese circuito con los comprobantes de lo que ella pagó; y (4) el conforme técnico firmado de cada etapa terminada.",
      doc="Expensas de mayo a septiembre 2026; facturas 4182/4191 (ROTH), 7 y 8 (Saczewiczyk), 92 (LO & CO), 99 y 101 (Gómez)"),
 dict(id="p3", tema="Trabajos dentro de unidades privadas", monto=42311875,
      pregunta="'Mantenimientos en unidades' sumó $42,3M en el ejercicio (20 % del gasto total; en julio fue el 31 % del mes). ¿Cuál es el criterio para pagar con expensas de todos trabajos dentro de departamentos privados? Entendemos que cañerías y columnas comunes sí corresponden; pedimos el criterio por escrito para pintura, placards y terminaciones interiores.",
      doc="Liquidaciones de enero a septiembre 2026, rubro Mantenimientos en unidades"),
 dict(id="p4", tema="Estado de caja y fondo de reserva", monto=1848489,
      pregunta="El estado financiero del ejercicio cierra con disponibilidades de $1.848.489: menos del 6 % de un mes de gastos ($32,2M en octubre). El saldo arrancó el ejercicio en $7,3M, y en julio y agosto las disponibilidades no cubrían las facturas pendientes. ¿Cuál es la composición actual de la caja (banco y efectivo por separado) y hay un plan para constituir un fondo de reserva que evite esta fragilidad?",
      doc="Estado financiero y estado patrimonial octubre 2025 – octubre 2026 (30/10/2026)"),
 dict(id="p5", tema="Deuda por expensas", monto=6126492,
      pregunta="La deuda por expensas pasó de $1,7M en enero a $6,1M en septiembre (15 unidades). El caso mayor es la cochera UC-1 (DEL VALLE), con $1,64M equivalentes a 14 meses. ¿Qué gestión de cobro se inició en cada caso, hay convenios de pago y cuáles pasaron a gestión judicial?",
      doc="Listado de deudores de la expensa de septiembre 2026"),
 dict(id="p6", tema="Presupuestos y conformidad de obras grandes", monto=21466750,
      pregunta="Para las dos obras más grandes del ejercicio — calefacción columna sector F ($11,67M, Peñaloza) y ascensor 3 ($9,8M, Laufken) — ¿pueden mostrar el presupuesto aprobado, si hubo más de una cotización, y el acta de conformidad o certificación del trabajo terminado? En la obra de calefacción, además, la factura del anticipo se emitió 11 días después del pago: ¿cuál es el circuito de aprobación previa?",
      doc="Expensas de enero a septiembre 2026; presupuestos 4001 (Laufken) y de Peñaloza"),
 dict(id="p7", tema="Detalle de octubre 2026", monto=32244604,
      pregunta="Octubre 2026 figura en el estado financiero con $32,2M de gastos, el segundo mes más caro del ejercicio. Sueldos y cargas suman $10,1M (contra ~$6M de promedio mensual) y mantenimientos en unidades $4,45M. ¿Pueden presentar la liquidación de octubre con sus comprobantes y, si el salto de sueldos corresponde a la liquidación final del encargado por la jubilación, el detalle de ese cálculo y los certificados del art. 80?",
      doc="Estado financiero octubre 2025 – octubre 2026, columnas de octubre 2026"),
 dict(id="p8", tema="Cobros pendientes del ejercicio", monto=30525973,
      pregunta="El estado patrimonial muestra 'cobros pendientes' por $30,5M al cierre, contra $18,5M al inicio del ejercicio: un aumento del 65 %. Entendemos que incluye las expensas del mes recién emitidas; pedimos que informen cuánto de ese monto es deuda vencida de ejercicios o meses anteriores, y cómo evolucionó esa deuda vencida durante el año.",
      doc="Estado patrimonial octubre 2025 – octubre 2026 (30/10/2026)"),
]

CONVOCATORIA = """Administración Almazare, RPA 5911.
Asamblea ordinaria del Consorcio de Propietarios Rivadavia 2067/69/71, el 17/11/2026 a las 19:00. Finalización prevista: 21:00.

Orden del día
1. Designación de presidente y secretario de la asamblea y 2 personas para rubricar el acta.
2. Validez de la asamblea.
3. Aprobación del ejercicio octubre 2025 a octubre 2026.
4. Ratificación o rectificación de la administración actual.
5. Ratificación o rectificación del Consejo de Propietarios.
6. Continuidad o no del conservador del ascensor; presupuestos.
7. Tema calefacción: nueva pérdida en el cuerpo A, 9º y 8º; presupuestos.
8. Desprendimiento de mampostería; presupuestos de reparaciones.
9. Recursos para los trabajos y orden de prioridades.

Nota de la convocatoria: el Código Civil y Comercial no considera el quórum de las dos convocatorias; se espera la concurrencia de los propietarios a las 19:00. De no reunirse el 50 % + 1 de la totalidad de los propietarios, las decisiones que tomen en mayoría los presentes se consideran "proposiciones", que quedan convalidadas si no reciben objeciones en contrario de los propietarios ausentes, en suficiente mayoría, luego de circularizarlas por escrito o por Redconar. Transcurrido el plazo de 15 días, las proposiciones quedan firmes (art. 2060 CCyC) y se constituyen en mandatos.
Quien no pueda asistir puede hacerse representar con el poder adjunto, previa firma en el libro de firmas en poder de la administración.

Graciela C. de Almazare — Administradora, RPA 5911"""

PODER = """CARTA PODER (imprimir y completar todos los datos antes de entregar; requiere firma previa en el libro de firmas de la administración, para cotejo)

En mi carácter de propietario de la unidad N° ______ del Consorcio de Propietarios del edificio de la calle Rivadavia 2067/69/71 de Capital Federal, autorizo a ______________________________, DNI N° ______________, a representarme en la asamblea ordinaria que se celebrará el día 17 de noviembre de 2026 a las 19:00 horas, facultándolo al efecto para que en mi nombre y representación intervenga en las deliberaciones, votando y decidiendo cuando fuera necesario.
Se extiende la presente en Buenos Aires, a los ____ días del mes de noviembre de 2026.            Firma: ______________________"""
