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
                  FROM hallazgos h WHERE h.liquidacion_id = l.id AND h.publicado
                    AND h.severidad IN ('CRÍTICO','ALTO')
                    -- los 4 de "pago en efectivo" (32,34,35,4) no se publican en la app:
                    -- el registro de caja dice EFECTIVO pero el dueño indica que el medio real fue otro
                    AND h.id NOT IN (32,34,35,4)),
    'hallazgos_revision', (SELECT count(*) + (SELECT count(*) FROM hallazgos h2
                     WHERE h2.liquidacion_id = l.id AND h2.publicado AND h2.id IN (32,34,35,4))
                  FROM hallazgos h WHERE h.liquidacion_id = l.id AND NOT h.publicado)
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
