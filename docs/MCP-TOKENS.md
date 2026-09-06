# Tokens del MCP — crear, listar y revocar

Cada persona que usa el MCP tiene su propio token (su propia URL). Revocar uno no afecta a los demás.
Todo se administra por consola en la máquina donde corre el stack:

```bash
cd /opt/consorcios-transparentes
```

## Crear

```bash
docker compose exec api python cli.py mcp-token crear <nombre>
# ej.: docker compose exec api python cli.py mcp-token crear amigo-juan
```

Imprime la URL completa **una única vez** — guardala/pasala en el momento, porque en la base queda
solo el hash y no se puede volver a mostrar. Si se pierde: revocar y crear de nuevo.

El `<nombre>` identifica a la persona (minúsculas y guiones, p.ej. `amigo-juan`, `consejo-marta`);
es único y aparece en los logs cada vez que esa persona consulta.

## Listar

```bash
docker compose exec api python cli.py mcp-token listar
# → amigo: activo — creado 2026-09-06 17:20 UTC
```

Muestra nombre, estado y fecha de creación. Nunca muestra tokens ni hashes.

## Revocar

```bash
docker compose exec api python cli.py mcp-token revocar <nombre>
```

Hace efecto en **≤ 1 minuto** (el servidor cachea las validaciones 60 segundos). La persona pasa a
recibir 404, igual que si nunca hubiera tenido acceso. Para restituirla: crear un token nuevo
(con otro nombre, o revocado el viejo, el mismo).

## Notas

- **El token maestro** (`CT_MCP_TOKEN` del `.env` raíz) es independiente de esta lista: es el del
  administrador y se rota editando el `.env` + `docker compose up -d mcp`.
- **Quién usa qué**: cada validación de un token con nombre queda logueada — `docker compose logs mcp`
  muestra quién estuvo consultando.
- **Ante una filtración**: revocar ese nombre alcanza; el resto sigue andando sin cambios.
- La guía para entregar junto con la URL está en `docs/MCP.md`.
