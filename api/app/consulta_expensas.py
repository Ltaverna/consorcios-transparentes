"""Chat de expensas: responde preguntas sobre los gastos del ejercicio con la API de Claude.

El modelo recibe un contexto compacto pero completo (totales por rubro/proveedor/mes +
la lista de gastos individuales) armado desde la base, y responde SOLO con esos datos.
La API key vive en el backend (settings.anthropic_api_key); nunca en el cliente.
El contexto va en un bloque cacheado (prompt caching) para que repetir preguntas sea barato.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings

SYSTEM_BASE = (
    "Sos un asistente de datos de las expensas de un consorcio (edificio Rivadavia 2069), "
    "para una asamblea de rendición de cuentas. Respondés preguntas de los propietarios sobre "
    "en qué se gastó la plata del edificio. Reglas:\n"
    "- Usá ÚNICAMENTE los datos del contexto. Si algo no está, decí que no figura en los datos "
    "cargados y sugerí mirar la pestaña Expensas o preguntarlo a la administración. No inventes.\n"
    "- Montos en pesos argentinos, con punto de miles (ej: $1.234.567).\n"
    "- Español rioplatense, conciso y claro. No des conclusiones acusatorias sobre personas; "
    "describí hechos (montos, proveedores, fechas).\n"
    "- Cuando una comparación o evolución se entienda mejor con un gráfico, además del texto "
    "completá el campo 'grafico' con datos simples (2 a 12 valores). Si no aporta, dejalo vacío.\n"
    "- El ejercicio va de octubre 2025 a octubre 2026 (13 meses). Respondé siempre con la herramienta responder."
)

_TOOL = {
    "name": "responder",
    "description": "Devuelve la respuesta para el propietario y, opcionalmente, datos para un gráfico simple.",
    "input_schema": {
        "type": "object",
        "properties": {
            "texto": {"type": "string", "description": "La respuesta en español rioplatense, concisa."},
            "grafico": {
                "type": "object",
                "description": "Opcional. Solo si un gráfico ayuda a entender la respuesta.",
                "properties": {
                    "tipo": {"type": "string", "enum": ["barras", "lineas", "torta"]},
                    "titulo": {"type": "string"},
                    "datos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "etiqueta": {"type": "string"},
                                "valor": {"type": "number"},
                            },
                            "required": ["etiqueta", "valor"],
                        },
                    },
                },
                "required": ["tipo", "titulo", "datos"],
            },
        },
        "required": ["texto"],
    },
}

_MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _mes(periodo: str) -> str:
    try:
        a, m = periodo.split("-")
        return f"{_MESES[int(m)].capitalize()} {a}"
    except Exception:
        return periodo


def _plata(v) -> str:
    try:
        return "$" + f"{float(v):,.0f}".replace(",", ".")
    except Exception:
        return str(v)


# Cache del contexto en memoria: se rearma solo si cambia la cantidad de gastos o liquidaciones.
_cache = {"firma": None, "texto": ""}


def construir_contexto(db: Session) -> str:
    firma = db.execute(text(
        "SELECT count(*) FROM gastos")).scalar(), db.execute(text(
        "SELECT count(*) FROM liquidaciones WHERE estado='procesada'")).scalar()
    if _cache["firma"] == firma and _cache["texto"]:
        return _cache["texto"]

    liqs = db.execute(text(
        "SELECT periodo, datos->>'total_gastos' AS tg, datos->>'total_deudores' AS td, "
        "(datos->>'cuadra')::bool AS cuadra FROM liquidaciones WHERE estado='procesada' "
        "ORDER BY periodo")).mappings().all()
    total_ej = sum(float(r["tg"] or 0) for r in liqs)

    cats = db.execute(text(
        "SELECT g.categoria, sum(g.importe) AS t FROM gastos g GROUP BY g.categoria ORDER BY t DESC")).all()
    provs = db.execute(text(
        "SELECT g.proveedor, round(sum(g.importe)::numeric,2) AS t, count(*) AS n "
        "FROM gastos g GROUP BY g.proveedor ORDER BY t DESC")).all()
    gastos = db.execute(text(
        "SELECT l.periodo, g.proveedor, g.categoria, g.importe, g.factura_nro, left(g.concepto,80) AS c "
        "FROM gastos g JOIN liquidaciones l ON l.id=g.liquidacion_id "
        "WHERE l.estado='procesada' ORDER BY l.periodo, g.importe DESC")).mappings().all()
    # Deudores del último período
    ult = liqs[-1]["periodo"] if liqs else None
    deudores = []
    if ult:
        row = db.execute(text(
            "SELECT datos->'deudores' AS d FROM liquidaciones WHERE periodo=:p"), {"p": ult}).scalar()
        deudores = row or []

    P = []
    P.append(f"EJERCICIO octubre 2025 – octubre 2026. Total gastado: {_plata(total_ej)}. "
             f"{len(liqs)} liquidaciones, todas auditadas y cuadran al centavo.")
    P.append("\nGASTO POR RUBRO (todo el ejercicio):")
    for c, t in cats:
        P.append(f"- {c}: {_plata(t)} ({t/total_ej*100:.1f}%)")
    P.append("\nTOTAL POR PROVEEDOR (todo el ejercicio, de mayor a menor):")
    for pr, t, n in provs:
        P.append(f"- {pr}: {_plata(t)} ({n} pago/s)")
    P.append("\nGASTO POR MES:")
    for r in liqs:
        P.append(f"- {_mes(r['periodo'])}: {_plata(r['tg'])}"
                 + (f" | deuda acumulada {_plata(r['td'])}" if r["td"] else ""))
    if deudores:
        P.append(f"\nDEUDORES al último mes ({_mes(ult)}):")
        for d in deudores:
            P.append(f"- {d.get('piso_depto', d.get('uf', ''))} {d.get('propietario', '')}: {_plata(d.get('deuda', 0))}")
    P.append("\nGASTOS INDIVIDUALES (período | proveedor | rubro | importe | factura | concepto):")
    for g in gastos:
        P.append(f"{g['periodo']} | {g['proveedor']} | {g['categoria']} | {_plata(g['importe'])} | "
                 f"{g['factura_nro'] or '-'} | {g['c']}")

    _cache["firma"], _cache["texto"] = firma, "\n".join(P)
    return _cache["texto"]


def responder(db: Session, pregunta: str, historial: list | None = None) -> dict:
    import anthropic
    contexto = construir_contexto(db)
    msgs = []
    for h in (historial or [])[-6:]:
        rol = "assistant" if h.get("rol") == "asistente" else "user"
        txt = (h.get("texto") or "").strip()
        if txt:
            msgs.append({"role": rol, "content": txt})
    msgs.append({"role": "user", "content": pregunta.strip()[:500]})

    cli = anthropic.Anthropic(api_key=settings.anthropic_api_key2 or settings.anthropic_api_key)
    msg = cli.messages.create(
        model=settings.chat_modelo, max_tokens=1200,
        system=[{"type": "text", "text": SYSTEM_BASE},
                {"type": "text", "text": contexto, "cache_control": {"type": "ephemeral"}}],
        tools=[_TOOL], tool_choice={"type": "tool", "name": "responder"},
        messages=msgs)
    for b in msg.content:
        if getattr(b, "type", None) == "tool_use":
            out = b.input or {}
            g = out.get("grafico")
            if not (isinstance(g, dict) and g.get("datos")):
                out.pop("grafico", None)
            return {"texto": out.get("texto", ""), "grafico": out.get("grafico")}
    return {"texto": "No pude generar una respuesta. Probá reformular la pregunta.", "grafico": None}
