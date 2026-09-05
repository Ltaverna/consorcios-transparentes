# Reglas de mercado + biblioteca de normativa (diseño aprobado 05-09-2026)

Tres reglas nuevas del motor que comparan la liquidación contra referencias de mercado cargadas por el
auditor (escala SUTERH, honorarios, abonos), y una biblioteca chica de normativa de respaldo en el panel.
Decisión central: las referencias son **config editable en el panel** (los valores cambian con cada
paritaria; el auditor los actualiza y el sistema nunca inventa datos — referencia en 0 = regla apagada).

## 1. Engine — `Config` con referencias

Campos nuevos en la dataclass `Config` de `engine/ct/rules.py` (floats, editables desde Consorcio como
los umbrales existentes; default 0 = regla apagada, salvo las tolerancias):

- `sueldo_encargado_ref` (neto mensual según escala vigente, lo calcula el auditor por paritaria)
- `sueldo_tolerancia` (default 0.10)
- `honorarios_ref` (monto mensual de referencia) y `honorarios_tolerancia` (default 0.10)
- `abono_ascensores_ref`, `abono_matafuegos_ref`, `abono_limpieza_ref` (tope mensual por rubro)

## 2. Engine — reglas (patrón `@rule`, claves estables, fixtures reales)

- **`sueldo_mercado`**: suma de sueldos netos del mes vs `sueldo_encargado_ref` con banda
  `±sueldo_tolerancia`. Ambas direcciones: por encima → "X % sobre la referencia de escala" (MEDIO;
  ALTO si supera el doble de la tolerancia); por debajo → "X % bajo la escala — verificar si hay pagos
  fuera de recibo" (ALTO siempre: pagar bajo escala es indicio serio).
- **`honorarios_mercado`**: honorarios de administración del mes vs `honorarios_ref + tolerancia`.
  Solo hacia arriba (MEDIO; ALTO al doble de la tolerancia).
- **`abonos_mercado`**: detección de abonos por palabras clave en concepto/proveedor (ascensor,
  matafuego/extinguidor, limpieza — constantes del módulo, estilo de detección de las reglas existentes);
  cada abono detectado vs su tope → MEDIO con rubro y referencia en la evidencia.

Evidencia: siempre los dos montos y la fuente ("referencia cargada por el auditor"); recomendación:
pedir justificación de la diferencia. Referencia en 0 → la regla no emite nada.

## 3. API/Panel — biblioteca de normativa (equipo-solo)

- Slots fijos (PDF, tope 20 MB): `escala-suterh`, `acuerdo-paritario`, `referencia-honorarios`;
  claves de storage `consorcio/normativa/{tipo}.pdf`.
- `POST /consorcio/normativa/{tipo}` (auditor) · `GET /consorcio/normativa` (estado {tipo: bool}) ·
  `GET /consorcio/normativa/{tipo}` (descarga forzada vía `_servir`). Lectura con
  `requiere("auditor", "consejo", "moderador")` — es material de trabajo del triage, NO para propietarios.
- Panel: en Consorcio (bloque de auditor existente), Card "Normativa de referencia" con los tres slots
  (estado + subir/reemplazar), junto a la del reglamento.
- Los umbrales nuevos de `Config` aparecen en el editor de umbrales existente (lee los campos de la
  dataclass dinámicamente — verificarlo en el plan; si el editor filtra por lista, sumarlos).

## 4. Carga inicial (operativa, al cierre del plan)

Investigación con fuentes citadas de los valores vigentes (escala SUTERH del período para la categoría
del edificio, referencia de honorarios) → validación del auditor → carga de valores por el panel y de
los PDFs de respaldo en la biblioteca. Los valores nunca van al repo (viven en la base).

## 5. Pruebas

- Engine (~+6): por regla: dispara con el fixture real y referencia baja/alta, no dispara dentro de la
  banda, silencio con referencia 0. El caso "bajo escala" de sueldos con severidad ALTO.
- API (+2): normativa — subir requiere auditor y sirve al equipo; propietario → 403; slots inválidos → 404.
- Web (+1): la Card de normativa solo aparece para auditor.

## Fuera de alcance

Modelar la escala SUTERH completa (categorías/antigüedad/zonas), actualización automática de referencias,
normativa visible a propietarios, comparación de abonos contra edificios comparables (requiere datos de
terceros que no existen todavía).
