# Contenido de la asamblea - Rivadavia 2067/69/71
# Asamblea extraordinaria del 20/10/2026 (convocatoria de la administración Almazare, 13/10/2026).
ASAMBLEA = dict(
    titulo="Asamblea extraordinaria",
    fecha="2026-10-20",        # ISO; la UI la formatea en es-AR
    hora="19:00",
    nota="En la planta baja del edificio, cierre previsto 20:30. Si no podés asistir, dejá la carta poder (está en Documentos → Convocatoria y poder; requiere firma previa en el libro de la administración).",
    notificacion=None,          # fecha ISO de notificación a los ausentes (plazo art. 2060). None = se estima 15 días desde la asamblea.
)

AGENDA = [
 dict(id="1", titulo="Designación de presidente, secretario y dos firmantes del acta",
      decidir="Elegir quién preside la asamblea, quién toma el acta y dos propietarios que la rubrican.",
      guia="Conviene que presida un propietario y no la administración. Anotar nombres y unidades para el acta.", mocion=None),
 dict(id="2", titulo="Validez de la asamblea",
      decidir="Constatar quórum: presentes más poderes, en unidades y en porcentual, sobre el total de 116 unidades y 99,91 %.",
      guia="Con 50 % + 1 del total (59 unidades y más de 49,96 %) las decisiones son firmes. Si no, lo votado queda como proposición y se circula 15 días (art. 2060 CCyC). La app lo calcula en la pestaña Votar.", mocion=None),
 dict(id="3", titulo="Informe: extinción del contrato del encargado por jubilación (art. 252 LCT)",
      decidir="Punto informativo: la administración notifica la extinción de pleno derecho del contrato de Ramón González por obtener su jubilación. No se vota; se escucha y se pregunta.",
      guia="Pedir el respaldo formal de cada paso: la intimación previa del art. 252 (fecha y constancia), el otorgamiento del beneficio, la notificación del cese, la baja registral, la liquidación final y qué pasó con ART y aportes. Las preguntas detalladas están en Documentos → Encargado ('La situación laboral al día de la asamblea').", mocion=None),
 dict(id="4", titulo="Nuevo contrato laboral con Ramón González como jubilado (art. 253 LCT), con vivienda",
      decidir="Aprobar o no la celebración de un nuevo contrato laboral con Ramón González en su calidad de jubilado, incluyendo el uso de la vivienda del encargado. El Consejo expone las consecuencias administrativas, legales y económicas.",
      guia="Antes de votar, pedir el texto o los puntos del contrato: plazo, tareas y alcance, remuneración, la vivienda como prestación accesoria por escrito, cómputo de antigüedad (art. 253), examen preocupacional y alta en ART. Pedir también el costo anual comparado contra la alternativa de reemplazo. La matriz de preguntas está en Documentos → Encargado.",
      mocion="Nuevo contrato laboral con Ramón González (art. 253), con vivienda"),
 dict(id="5", titulo="Organización del personal durante la transición",
      decidir="Definir cómo se cubren limpieza, mantenimiento y atención del edificio durante la transición, según lo decidido en el punto 4.",
      guia="Pedir un plan concreto: quién hace cada tarea, con qué horarios, qué costo mensual tiene y por cuánto tiempo. Si participa el ayudante, dejar claro su rol y su carga horaria. Comparar el costo del esquema propuesto contra el actual antes de aprobar.",
      mocion="Aprobar el esquema de personal para la transición"),
]

# Preguntas a la administración: vaciadas tras la asamblea del 3/09/2026 (eran de las
# expensas de julio/agosto). Quedan en el historial de git; las de la asamblea nueva se
# cargan acá cuando se defina la convocatoria. Las del encargado están en encargado.md.
PREGUNTAS = []

CONVOCATORIA = """Administración Almazare, RPA 5911. Ciudad de Buenos Aires, 13 de octubre de 2026.
Asamblea extraordinaria del Consorcio de Propietarios Rivadavia 2067/69/71 (CUIT 33-60039145-9), el 20/10/2026 a las 19:00 en la planta baja del edificio. Finalización prevista: 20:30.

Orden del día
1. Designación de presidente y secretario de la asamblea y 2 personas para rubricar el acta.
2. Validez de la asamblea.
3. Informe de la administración: notificación al consorcio de la extinción de pleno derecho del contrato laboral del encargado, Sr. Ramón González, por obtención de su beneficio jubilatorio (art. 252, Ley de Contrato de Trabajo).
4. Tratamiento y decisión sobre la propuesta de celebración de un nuevo contrato laboral (art. 253 LCT) con el Sr. Ramón González en su calidad de trabajador pasivo/jubilado, incluyendo el uso de la unidad vivienda correspondiente. El Consejo de Administración expondrá las características y consecuencias, tanto administrativas como legales y económicas, de celebrarse o no este nuevo contrato.
5. Organización y reestructuración del personal para las tareas de limpieza, mantenimiento y atención del edificio que se aplicará durante la transición generada por la nueva situación, tomando en cuenta lo decidido en el punto 4.

Nota de la convocatoria: el Código Civil y Comercial no considera el quórum de las dos convocatorias; se espera la concurrencia de los propietarios a las 19:00. De no reunirse el 50 % + 1 de la totalidad de los propietarios, las decisiones que tomen en mayoría los presentes se consideran "proposiciones", que quedan convalidadas si no reciben objeciones en contrario de los propietarios ausentes, en suficiente mayoría, luego de circularizarlas por escrito o por Redconar. Transcurrido el plazo de 15 días, las proposiciones quedan firmes (art. 2060 CCyC) y se constituyen en mandatos.
Quien no pueda asistir puede hacerse representar con el poder adjunto, previa firma en el libro de firmas en poder de la administración.

Graciela C. de Almazare — Administradora, RPA 5911"""

PODER = """CARTA PODER (imprimir y completar todos los datos antes de entregar; requiere firma previa en el libro de firmas de la administración, para cotejo)

En mi carácter de propietario de la unidad N° ______ del Consorcio de Propietarios del edificio de la calle Rivadavia 2067/69/71 de Capital Federal, autorizo a ______________________________, DNI N° ______________, a representarme en la asamblea extraordinaria que se celebrará el día 20 de octubre de 2026 a las 19:00 horas, facultándolo al efecto para que en mi nombre y representación intervenga en las deliberaciones, votando y decidiendo cuando fuera necesario.
Se extiende la presente en Buenos Aires, a los ____ días del mes de octubre de 2026.            Firma: ______________________"""
