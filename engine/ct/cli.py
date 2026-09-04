"""Línea de comandos: python -m ct analizar <liquidacion.pdf|.txt> [--anterior <pdf|txt>] [--json salida.json]"""
from __future__ import annotations
import argparse
import json
import sys

from .redconar import parse_pdf, parse_text
from .rules import Config, evaluar
from .comprobantes import cargar_manifiesto_redconar, cruzar
from .informe import informe_excel, informe_html


def load(path: str):
    if path.lower().endswith(".pdf"):
        return parse_pdf(path)
    return parse_text(open(path, encoding="utf-8").read())


def fmt(v: float) -> str:
    return ("-" if v < 0 else "") + "$" + f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ct", description="Consorcio Transparente: análisis de liquidaciones de expensas")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analizar", help="Leer, validar y evaluar una liquidación")
    a.add_argument("liquidacion")
    a.add_argument("--anterior", help="Liquidación del mes anterior para comparar")
    a.add_argument("--json", help="Guardar el resultado completo en JSON")
    a.add_argument("--solo-cuadre", action="store_true", help="Solo mostrar las verificaciones de cuadre")
    a.add_argument("--comprobantes", help="Carpeta con los comprobantes descargados del portal")
    a.add_argument("--manifiesto", help="manifest.json de la descarga (formato Redconar)")
    a.add_argument("--mes", help="Prefijo de mes del manifiesto a usar, por ejemplo 2026-08")
    a.add_argument("--excel", help="Generar informe Excel (.xlsx)")
    a.add_argument("--html", help="Generar informe HTML")
    a.add_argument("--marca", default="", help="Nombre o marca que encabeza el informe")
    args = ap.parse_args(argv)

    liq = load(args.liquidacion)
    prev = load(args.anterior) if args.anterior else None
    print(f"{liq.consorcio or '(consorcio)'} · {liq.periodo} · {liq.administracion} · sistema {liq.sistema}")
    print(f"Gastos: {len(liq.gastos)} líneas, {fmt(liq.suma_gastos)} · Unidades: {len(liq.unidades)} · Deudores: {len(liq.deudores)} por {fmt(liq.total_deudores or 0)}")
    bad = [c for c in liq.checks if not c.ok]
    print(f"Cuadre: {len(liq.checks) - len(bad)}/{len(liq.checks)} verificaciones OK" + ("" if not bad else " · FALLAN: " + "; ".join(f"{c.nombre} (dif {fmt(c.diff)})" for c in bad)))
    for av in liq.avisos:
        if "no suman" not in av:
            print("  aviso:", av)
    if args.solo_cuadre:
        return 0 if not bad else 1
    hs = evaluar(liq, prev, Config())
    docs = []
    if args.comprobantes and args.manifiesto:
        items = cargar_manifiesto_redconar(args.manifiesto, args.comprobantes, mes=args.mes)
        docs, hs2 = cruzar(liq, items)
        tipos = {}
        for d in docs:
            tipos[d.tipo] = tipos.get(d.tipo, 0) + 1
        print(f"Comprobantes: {len(docs)} documentos leídos ({', '.join(f'{k} {v}' for k, v in sorted(tipos.items()))})")
        hs = hs + hs2
        order = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}
        hs.sort(key=lambda h: (order.get(h.severidad, 9), -abs(h.monto)))
    print(f"\nHallazgos: {len(hs)}")
    for h in hs:
        print(f"\n[{h.severidad}] {h.area} · {h.titulo}")
        if h.evidencia:
            print("   Evidencia:", h.evidencia[:600])
        if h.monto:
            print("   Monto:", fmt(h.monto))
        if h.recomendacion:
            print("   Pedir:", h.recomendacion)
    if args.excel:
        informe_excel(liq, hs, args.excel, prev, docs, args.marca); print("Excel guardado en", args.excel)
    if args.html:
        informe_html(liq, hs, args.html, prev, docs, args.marca); print("HTML guardado en", args.html)
    if args.json:
        out = dict(liquidacion=liq.to_dict(), anterior=prev.to_dict() if prev else None, hallazgos=[h.to_dict() for h in hs], documentos=[d.to_dict() for d in docs])
        json.dump(out, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\nJSON guardado en", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
