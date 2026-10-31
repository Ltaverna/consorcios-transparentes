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
      guia="Dato a favor: las TRECE liquidaciones del ejercicio completo (octubre 2025 a octubre 2026) fueron auditadas de forma independiente, todas cuadran al centavo, y el gasto total del ejercicio ($302,8M) coincide exactamente con los estados presentados el 30/10. Las preguntas no son sobre el cuadre global sino sobre gastos puntuales. Antes de votar conviene pedir aclaración de los puntos abiertos (el detalle con montos y comprobantes está en la pestaña Preguntas y en Documentos → Expensas): la factura 183 de Peñaloza por $2,8M liquidada en febrero y también en marzo; la obra de calefacción y pisos de 12-B y 13-B ($18,5M en 13 facturas de 7 proveedores, con pagos que no fueron al emisor de la factura); el criterio para pagar con expensas trabajos dentro de unidades privadas; la caja, que cierra el ejercicio con $1,85M (menos del 6 % de un mes de gastos); y el detalle de la liquidación final del encargado pagada en octubre. Si algo no se responde en la asamblea, pedir que conste en acta el compromiso de responder por escrito con plazo.",
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
      guia="Laufken facturó $28,1M en 29 pagos durante el ejercicio completo: el abono mensual (que el análisis marcó por encima del tope de referencia en varios meses), la obra del ascensor 3 (~$9,8M: anticipo 50 % en enero y 4 cuotas de $1,85M) y trabajos en el ascensor 4. Pedir: los presupuestos alternativos que menciona la convocatoria, qué incluye cada abono (los 3 ascensores, repuestos, emergencias), el acta de conformidad de la obra del ascensor 3 y el estado del libro de inspección. No votar sin ver al menos dos presupuestos comparables.",
      mocion="Continuar con el conservador actual de ascensores"),
 dict(id="7", titulo="Calefacción: nueva pérdida en el cuerpo A, 9º y 8º — presupuestos",
      decidir="Aprobar la reparación de la nueva pérdida y con qué presupuesto.",
      guia="Sería la quinta intervención grande de calefacción del ejercicio: columna 11-B/12-B/13-B (saldo $3M, octubre 2025), columna 5-B/4-B/3-B ($8,2M), serpentinas 12-B y 13-B ($7,95M, ROTH, más la reconstrucción de pisos), columna sector F pisos 8-12 ($14M). Solo en calefacción ya se gastaron más de $33M en el ejercicio. Antes de aprobar otra reparación puntual, pedir un diagnóstico integral de la instalación: qué tramos quedan originales, cuántas pérdidas más son esperables y si conviene un plan por etapas con precio por columna. Pedir mínimo dos presupuestos con el mismo alcance por escrito (materiales, albañilería y terminación incluidas) y definir quién certifica el trabajo terminado.",
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
 dict(id="p9", tema="Contrataciones de Peñaloza en el ejercicio", monto=34990000,
      pregunta="Peñaloza Alejandro Roberto cobró $34.990.000 en 14 pagos durante el ejercicio (11,6 % del gasto total), todos de plomería y calefacción: cañerías de calefacción de 11-B/12-B/13-B (saldo $3M, octubre 2025), columna 5-B/4-B/3-B ($8,2M entre noviembre 2025 y enero 2026), bajadas 2-D/2-E ($5,6M — ver pregunta sobre la factura 183), cloaca de cochera y terraza ($2,65M), columna sector F pisos 8-12 ($14M: anticipo $5M más factura 202 de $9M en tres cuotas) y arreglos menores. Pedimos: (1) el presupuesto previo aprobado de cada trabajo y si se pidieron cotizaciones alternativas — en ningún caso consta comparación de presupuestos; (2) por qué en dos casos la factura se emitió después del pago (el anticipo de $5M se pagó 11 días antes de la factura, y en agosto la transferencia es 5 días anterior a la factura); (3) el criterio de prorrateo: el mismo trabajo del sector F se liquidó en clase A un mes y en clase D el siguiente; y (4) el conforme técnico firmado de cada trabajo terminado, con el croquis de los tramos de cañería cambiados.",
      doc="Expensas de octubre 2025 a octubre 2026; facturas 79, 81, 83, 84, 88, 90, 91, 183, 201, 202 y 207 de Peñaloza"),
 dict(id="p2", tema="Obra de calefacción y pisos en 12-B y 13-B", monto=18513799,
      pregunta="Entre mayo y septiembre la reparación de las serpentinas de calefacción de 12-B y 13-B y la reconstrucción de los pisos costó $18,5M pagados por expensas: cambio de serpentinas $7.950.000 (ROTH, facturas 4182/4191), rotura y recolocación de piso en 13-B $5.252.000 (Saczewiczyk), porcelanato $2.003.457 (LO & CO), contrapiso 13-B y cielorraso 12-B $2.600.000 (Gómez), plastificado de pisos 12-B $400.000, alquiler de equipos $205.392 y materiales $102.950. Pedimos: (1) el informe del siniestro que originó la obra y el presupuesto total aprobado antes de empezar — en las expensas el gasto aparece repartido en 13 facturas de 7 proveedores a lo largo de 5 meses, sin un presupuesto integral visible; (2) el criterio de alcance: el cambio de serpentina es instalación común, pero ¿la reposición de porcelanato de primera marca, el plastificado y la pintura interior corresponden al consorcio o al propietario?; (3) el circuito de pagos: la factura del porcelanato dice 'abonadas por dpto 13ºB', la de LEV Rental está a nombre de la propietaria del 13-B y varios pagos se transfirieron a su cuenta y no a la del proveedor que facturó — si la propietaria adelantó pagos y el consorcio le reembolsó, que se documente ese circuito con los comprobantes de lo que ella pagó; (4) el conforme técnico firmado de cada etapa terminada; y (5) un antecedente que pedimos aclarar: en octubre de 2025 se pagó a Peñaloza el saldo de un cambio de cañerías de calefacción que incluyó justamente 11-B, 12-B y 13-B ($3.000.000) — ¿qué relación hay entre ese trabajo y la falla de las serpentinas de los mismos departamentos pocos meses después, y quién respondió por la garantía?",
      doc="Expensas de octubre 2025 y de mayo a septiembre 2026; facturas 81 (Peñaloza), 4182/4191 (ROTH), 7 y 8 (Saczewiczyk), 92 (LO & CO), 99 y 101 (Gómez)"),
 dict(id="p10", tema="Autorización y seguro de la obra del 13-B", monto=18513799,
      pregunta="Sobre la misma obra de 12-B y 13-B ($18,5M): (1) ¿qué instancia autorizó el gasto — administración sola, consejo o asamblea — y dónde consta esa decisión? Es el gasto extraordinario más grande del ejercicio y no pasó por asamblea; (2) el consorcio paga todos los meses el Seguro Integral (Allianz, póliza 250230772503): ¿se denunció el siniestro a la aseguradora y qué respondió? Si no se denunció, ¿por qué?; y (3) el proveedor principal del piso (Saczewiczyk, $5,25M) facturó con numeración 7 y 8, es decir casi sin actividad previa: ¿cómo se lo seleccionó y qué antecedentes de trabajo tiene?",
      doc="Expensas de julio y agosto 2026; póliza Allianz 250230772503; facturas 7 y 8 de Saczewiczyk"),
 dict(id="p11", tema="Pagos a la cuenta de una propietaria", monto=3457392,
      pregunta="En la obra del 13-B, pagos que el consorcio hizo contra facturas de Saczewiczyk (saldo de $2.552.000 y pintura de $700.000) y de LEV Rental ($205.392) se transfirieron a la cuenta de Acosta Rosana, propietaria del 13-B, y no a la del proveedor que emitió cada factura. Pedimos que se explique por qué el dinero del consorcio salió a la cuenta de una propietaria: si ella adelantó esos pagos a los proveedores y el consorcio le reintegró, que se acompañen los comprobantes de lo que efectivamente pagó a cada uno; y que a futuro todo pago salga directo de la cuenta del consorcio al proveedor que factura.",
      doc="Expensas de julio y agosto 2026; comprobantes de transferencia a nombre de Acosta Rosana"),
 dict(id="p3", tema="Trabajos dentro de unidades privadas", monto=56785208,
      pregunta="'Mantenimientos en unidades' sumó $56,8M en el ejercicio completo (18,8 % del gasto total; en julio fue el 31 % del mes). ¿Cuál es el criterio para pagar con expensas de todos trabajos dentro de departamentos privados? Entendemos que cañerías y columnas comunes sí corresponden; pedimos el criterio por escrito para pintura, placards y terminaciones interiores.",
      doc="Liquidaciones de octubre 2025 a octubre 2026, rubro Mantenimientos en unidades"),
 dict(id="p4", tema="Estado de caja y fondo de reserva", monto=1848489,
      pregunta="El estado financiero del ejercicio cierra con disponibilidades de $1.848.489: menos del 6 % de un mes de gastos ($32,2M en octubre). El saldo arrancó el ejercicio en $7,3M, y en julio y agosto las disponibilidades no cubrían las facturas pendientes. ¿Cuál es la composición actual de la caja (banco y efectivo por separado) y hay un plan para constituir un fondo de reserva que evite esta fragilidad?",
      doc="Estado financiero y estado patrimonial octubre 2025 – octubre 2026 (30/10/2026)"),
 dict(id="p5", tema="Deuda por expensas", monto=6126492,
      pregunta="La deuda por expensas creció durante el ejercicio (de $1,7M en enero a más de $6M). El caso mayor es la cochera UC-1 (DEL VALLE): a octubre acumula $1.871.040, equivalentes a 21,9 meses de expensa (en septiembre eran 14 meses) y al 37 % de toda la deuda del edificio. ¿Qué gestión de cobro se inició en cada caso, hay convenios de pago y cuáles pasaron a gestión judicial?",
      doc="Listado de deudores de las expensas de septiembre y octubre 2026"),
 dict(id="p6", tema="Presupuestos y conformidad de obras grandes", monto=23800000,
      pregunta="Para las dos obras más grandes del ejercicio — calefacción columna sector F ($14M, Peñaloza: anticipo $5M más factura 202 de $9M) y ascensor 3 ($9,8M, Laufken) — ¿pueden mostrar el presupuesto aprobado, si hubo más de una cotización, y el acta de conformidad o certificación del trabajo terminado? En la obra de calefacción, además, la factura del anticipo se emitió 11 días después del pago: ¿cuál es el circuito de aprobación previa?",
      doc="Expensas de julio a octubre 2026; presupuestos 4001 (Laufken) y de Peñaloza"),
 dict(id="p7", tema="Liquidación final del encargado", monto=3981659,
      pregunta="La liquidación de octubre (ya auditada: cuadra) muestra sueldos por $10,1M porque se pagaron juntos los sueldos de septiembre y de octubre, y el recibo 601392 de Ramón González es de $3.981.659 — más del doble de su sueldo habitual, consistente con la liquidación final por la jubilación (art. 252). Pedimos el detalle de ese cálculo (SAC proporcional, vacaciones no gozadas; corresponde verificar que esté completo y correcto), la entrega de los certificados del art. 80, y la fecha de alta del nuevo contrato como jubilado (art. 253) aprobado en la asamblea del 20/10.",
      doc="Liquidación de octubre 2026, recibo 601392; carta documento del 9/10"),
 dict(id="p8", tema="Cobros pendientes del ejercicio", monto=30525973,
      pregunta="El estado patrimonial muestra 'cobros pendientes' por $30,5M al cierre, contra $18,5M al inicio del ejercicio: un aumento del 65 %. Entendemos que incluye las expensas del mes recién emitidas; pedimos que informen cuánto de ese monto es deuda vencida de ejercicios o meses anteriores, y cómo evolucionó esa deuda vencida durante el año.",
      doc="Estado patrimonial octubre 2025 – octubre 2026 (30/10/2026)"),
 dict(id="p12", tema="Servicio de cámaras a nombre del encargado", monto=87703,
      pregunta="El servicio de internet de las cámaras de seguridad del edificio (FLOW) viene facturado a nombre personal de Ramón González, el encargado, y no del consorcio. Se repite todos los meses (noviembre 2025, diciembre, agosto, septiembre y octubre 2026, entre $64.000 y $88.000 mensuales). Pedimos que la cuenta se ponga a nombre del consorcio (CUIT 33-60039145-9), para que el servicio no quede atado a la persona del empleado y la factura sea del consorcio.",
      doc="Expensas de noviembre 2025 a octubre 2026; facturas de FLOW"),
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
