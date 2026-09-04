# Asamblea Rivadavia 2069 — app integrada (diseño aprobado 03-09-2026)

Asamblea extraordinaria del 3/09/2026, 19:00. Público: todos los propietarios (link asamblea.neuralcore.dev).
Objetivos: confrontar a la administración con datos, que las decisiones queden bien tomadas (quórum, doble mayoría, art. 2060),
ordenar la discusión por punto, y que los ausentes puedan seguir y objetar dentro de los 15 días.

## Estructura (una sola página, pestañas)
1. **Agenda** — los 6 puntos de la convocatoria como tarjetas: estado (pendiente / en curso / tratado), hora de inicio y fin,
   qué hay que decidir, moción asociada y su resultado en vivo. Lista de oradores ("Pedir la palabra": unidad + nombre; cola visible;
   el moderador da o quita la palabra). Mociones precargadas para los puntos 3, 5 y 6.
2. **Votar** — la app existente (presentes, poderes, votos, pasar lista, exportar). Marcar requiere modo moderador.
3. **Preguntas** — hallazgos del informe de expensas formulados como preguntas factuales a la administración, cada una con el
   documento exacto de Redconar que la respalda (sin publicar los PDF). El moderador registra la respuesta dada.
4. **Proposiciones** — si no hubo 50 % + 1 del total (unidades y porcentual), cada moción votada es "proposición" con vencimiento
   18/09/2026. Un propietario ausente registra su objeción (unidad, nombre, motivo). Se cuentan objeciones por unidades y porcentual.
   Criterio mostrado explícitamente: la proposición queda objetada si las objeciones alcanzan la mayoría de los ausentes (unidades y porcentual).
5. **Documentos** — convocatoria (texto), modelo de poder, informe de expensas completo (HTML en /informe-expensas.html),
   Excel del análisis (/analisis-expensas.xlsx), instrucciones de uso.
6. **Acta** — impresión ampliada: quórum, puntos con resultado, preguntas con respuestas, proposiciones y objeciones.

## Modo moderador
PIN 2069 (se guarda en el dispositivo). Habilita: marcar presentes/poderes/votos, cambiar estado de puntos, dar la palabra,
registrar respuestas, configurar mociones, reiniciar. Sin PIN se ve todo en vivo y se puede pedir la palabra y objetar.

## Datos
Misma hoja de Google (Apps Script). Estado ampliado: agenda{punto: {estado, inicio, fin, nota}}, palabra[], respuestas{},
objeciones{mocion: {uf: {nombre, motivo, ts}}}. Eventos nuevos: agenda, palabra, respuesta, objecion. Pestañas nuevas: Agenda, Objeciones.
El script debe volver a implementarse como nueva versión.

## Fuera de alcance hoy
Identificación por Redconar; hosting público de comprobantes; edición del reglamento interno dentro de la app.
