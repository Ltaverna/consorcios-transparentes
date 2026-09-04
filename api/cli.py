"""Comandos administrativos: python cli.py init|usuario|codigo ..."""
import argparse
import getpass

from app import admin
from app.db import Base, SessionLocal, engine


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
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
