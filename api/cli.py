"""Comandos administrativos: python cli.py init|usuario|codigo|embeddings|mcp-token ..."""
import argparse
import getpass

from app import admin, embeddings, models

URL_MCP = "https://mcp-consorcio.neuralcore.dev"
from app.db import Base, SessionLocal, engine
from app.storage import storage_por_defecto
from app.texto import extraer_texto

LOTE_EMBEDDINGS = 20


def backfill_embeddings(db, todos: bool = False) -> int:
    """Embebe los documentos con texto extraíble y embedding NULL (o todos si `todos=True`),
    en lotes con commit por lote (una corrida interrumpida no pierde lo ya embebido).
    Usar `--todos` para re-embeber al cambiar de modelo."""
    if not embeddings.habilitado():
        print("Error: CT_EMBEDDINGS_API_KEY no está configurada; no hay nada que hacer")
        return 1
    storage = storage_por_defecto()
    q = db.query(models.Documento).order_by(models.Documento.id)
    pendientes = q.all() if todos else q.filter(models.Documento.embedding.is_(None)).all()
    embebidos = salteados = fallidos = 0
    for i in range(0, len(pendientes), LOTE_EMBEDDINGS):
        lote = pendientes[i:i + LOTE_EMBEDDINGS]
        con_texto = [(d, t) for d in lote if (t := extraer_texto(storage, d))]
        salteados += len(lote) - len(con_texto)  # imágenes/escaneos: sin texto no hay embedding
        if not con_texto:
            continue
        vectores = embeddings.embeber([t for _, t in con_texto])
        if vectores is None:
            fallidos += len(con_texto)
            continue
        for (d, _), vector in zip(con_texto, vectores):
            d.embedding = vector
        db.commit()
        embebidos += len(con_texto)
    print(f"Embebidos: {embebidos} | salteados (sin texto): {salteados} | fallidos: {fallidos}")
    return 1 if fallidos else 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="ct-api")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="Crear las tablas y el consorcio")
    i.add_argument("nombre")
    i.add_argument("--direccion", default="")
    i.add_argument("--cuit", default="")
    u = sub.add_parser("usuario", help="Crear un usuario (pide la clave por consola)")
    u.add_argument("email"); u.add_argument("nombre"); u.add_argument("rol", choices=admin.ROLES)
    c = sub.add_parser("codigo", help="Generar el código de acceso de una unidad")
    c.add_argument("uf", type=int)
    emb = sub.add_parser("embeddings", help="Backfill: embeber documentos con texto y sin embedding")
    emb.add_argument("--todos", action="store_true",
                     help="Re-embeber TODOS los documentos (no solo los NULL); usar al cambiar de modelo")
    mt = sub.add_parser("mcp-token", help="Tokens de acceso al MCP por persona")
    mt_sub = mt.add_subparsers(dest="mcp_cmd", required=True)
    mt_sub.add_parser("crear", help="Crear un token y mostrar la URL (una sola vez)").add_argument("nombre")
    mt_sub.add_parser("revocar", help="Revocar el token de una persona").add_argument("nombre")
    mt_sub.add_parser("listar", help="Listar tokens (nombre, estado, creado; sin hashes)")
    args = ap.parse_args()

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if args.cmd == "init":
            con = admin.init_consorcio(db, args.nombre, direccion=args.direccion, cuit=args.cuit)
            print(f"Consorcio listo: {con.nombre} (id {con.id})")
            if con.nombre != args.nombre:
                print(f"Atención: el consorcio ya existía como '{con.nombre}'; no se modificó.")
        elif args.cmd == "usuario":
            clave = getpass.getpass("Clave: ")
            clave2 = getpass.getpass("Repetir clave: ")
            if clave != clave2:
                print("Error: las claves no coinciden")
                return 1
            usr = admin.crear_usuario(db, args.email, args.nombre, args.rol, clave)
            print(f"Usuario {usr.email} creado con rol {usr.rol}")
        elif args.cmd == "codigo":
            print(f"Código de la UF {args.uf}: {admin.generar_codigo(db, args.uf)} (guardalo: no se vuelve a mostrar)")
        elif args.cmd == "embeddings":
            return backfill_embeddings(db, todos=args.todos)
        elif args.cmd == "mcp-token":
            if args.mcp_cmd == "crear":
                token = admin.crear_mcp_token(db, args.nombre)
                print(f"URL del MCP para '{args.nombre}': {URL_MCP}/mcp/{token}")
                print("Guardala ahora: no se vuelve a mostrar (en la base queda solo el hash).")
            elif args.mcp_cmd == "revocar":
                admin.revocar_mcp_token(db, args.nombre)
                print(f"Token de '{args.nombre}' revocado (hace efecto en ≤1 minuto).")
            elif args.mcp_cmd == "listar":
                filas = admin.listar_mcp_tokens(db)
                if not filas:
                    print("No hay tokens MCP creados.")
                for t in filas:
                    estado = "activo" if t.activo else "revocado"
                    print(f"{t.nombre}: {estado} — creado {t.creado:%Y-%m-%d %H:%M} UTC")
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
