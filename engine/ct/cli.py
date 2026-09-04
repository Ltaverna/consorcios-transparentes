"""Línea de comandos: python -m ct analizar <liquidacion.pdf|.txt> [--anterior <pdf|txt>] [--json salida.json]"""
from __future__ import annotations
import argparse
import json
import sys

from .redconar import parse_pdf, parse_text
from .rules import Config, evaluar


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
    print(f"\nHallazgos: {len(hs)}")
    for h in hs:
        print(f"\n[{h.severidad}] {h.area} · {h.titulo}")
        if h.evidencia:
            print("   Evidencia:", h.evidencia[:600])
        if h.monto:
            print("   Monto:", fmt(h.monto))
        if h.recomendacion:
            print("   Pedir:", h.recomendacion)
    if args.json:
        out = dict(liquidacion=liq.to_dict(), anterior=prev.to_dict() if prev else None, hallazgos=[h.to_dict() for h in hs])
        json.dump(out, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\nJSON guardado en", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
