#!/usr/bin/env python3
"""Snapshot de expensas para la app de asamblea.

Lee las últimas liquidaciones procesadas de la base del panel (vía docker compose,
el Postgres no expone puerto al host) y escribe apps/asamblea/expensas.json
(GITIGNOREADO: datos derivados de liquidaciones no van al repo; sí se publican
en el HTML generado, decisión del dueño).

Uso:  python3 tools/expensas_snapshot.py [N_MESES]   (default 7)
"""
import json, subprocess, sys, os

N = int(sys.argv[1]) if len(sys.argv) > 1 else 7

# Criterio de "hallazgo verificado" para el app, aplicado a TODOS los meses (dato derivado,
# no cambia la base). Se muestran CRÍTICO/ALTO salvo el ruido que el dueño decidió no publicar:
# efectivo (el medio real fue otro), pagos a "Cuenta Banco" sin nombre, artefactos técnicos
# (archivo ya adjunto / comprobante ya respaldaba), transferencias de sueldos sin respaldo,
# volatilidad ("subió X%"), desvíos de escala salarial, y las transferencias cuenta/impuestos
# (BANCO/ARCA) que no son sobrepagos a proveedores.
EXCL = ("h.severidad IN ('CRÍTICO','ALTO') "
        "AND h.titulo NOT ILIKE '%efectivo%' AND h.titulo NOT ILIKE '%Cuenta Banco%' "
        "AND h.titulo NOT ILIKE '%ya respaldaba%' AND h.titulo NOT ILIKE '%mismo archivo está adjunto%' "
        "AND h.titulo NOT ILIKE '%transferencia declarada%no está respaldada%' "
        "AND h.titulo NOT ILIKE '%: subió %' AND h.titulo NOT ILIKE '%escala%' "
        "AND h.titulo NOT ILIKE '%sobre la referencia%' AND h.titulo NOT ILIKE '%Transferencia por %'")
SQL = f"""
SELECT COALESCE(jsonb_agg(j ORDER BY j->>'periodo'), '[]'::jsonb) FROM (
  SELECT jsonb_build_object(
    'periodo', l.periodo,
    'cuadra', l.cuadra,
    'total_gastos', l.datos->'total_gastos',
    'total_deudores', l.datos->'total_deudores',
    'deudores', COALESCE(l.datos->'deudores','[]'::jsonb),
    'categorias', COALESCE(l.datos->'totales_categoria','{{}}'::jsonb),
    'proveedores', (SELECT COALESCE(jsonb_agg(q.p ORDER BY q.total DESC),'[]'::jsonb) FROM (
        SELECT jsonb_build_object('proveedor', g.proveedor,
                                  'total', round(sum(g.importe)::numeric,2),
                                  'items', count(*)) AS p,
               sum(g.importe) AS total
        FROM gastos g WHERE g.liquidacion_id = l.id GROUP BY g.proveedor) q),
    'hallazgos', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
                     'sev', h.severidad, 'titulo', h.titulo, 'monto', h.monto,
                     'pedir', CASE
                        -- pagos triangulados de SACZEWICZYK: la pregunta central del dueño
                        WHEN h.id IN (33,61) THEN h.recomendacion || ' Que se explique qué trabajo concreto se realizó y por qué el pago salió por fuera de la cuenta del consorcio.'
                        WHEN h.id IN (8,22,24) THEN h.recomendacion || ' Detallar qué trabajos hizo este proveedor, con presupuestos y comprobantes.'
                        ELSE h.recomendacion END)
                     ORDER BY CASE h.severidad WHEN 'CRÍTICO' THEN 0 ELSE 1 END, h.monto DESC),'[]'::jsonb)
                  FROM hallazgos h WHERE h.liquidacion_id = l.id AND {EXCL}),
    'hallazgos_revision', (SELECT count(*) FROM hallazgos h
                  WHERE h.liquidacion_id = l.id AND h.severidad IN ('CRÍTICO','ALTO') AND NOT ({EXCL})),
    -- unidades slim SOLO del último período (para los botones Top 10 por UF / deudores con interés)
    'unidades', CASE WHEN l.periodo = (SELECT max(periodo) FROM liquidaciones WHERE estado='procesada')
       THEN (SELECT COALESCE(jsonb_agg(jsonb_build_object(
               'uf', u->'uf', 'pd', u->>'piso_depto', 'prop', u->>'propietario',
               'mes', u->'total_mes', 'pagar', u->'a_pagar', 'deuda', u->'deuda', 'inte', u->'interes')), '[]'::jsonb)
             FROM jsonb_array_elements(COALESCE(l.datos->'unidades','[]'::jsonb)) u)
       ELSE '[]'::jsonb END
  ) AS j
  FROM liquidaciones l
  WHERE l.estado = 'procesada'
  ORDER BY l.periodo DESC
  LIMIT {N}) t;
"""
raiz = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
out = subprocess.run(
    ["docker", "compose", "exec", "-T", "db", "psql", "-U", "consorcio", "-d", "consorcio", "-t", "-A", "-c", SQL],
    cwd=os.path.abspath(raiz), capture_output=True, text=True, check=True).stdout.strip()
datos = json.loads(out)
destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "expensas.json")
json.dump(datos, open(destino, "w", encoding="utf-8"), ensure_ascii=False)
print(f"ok: {len(datos)} períodos -> {os.path.abspath(destino)}")
