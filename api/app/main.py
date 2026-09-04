from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import auth, consorcio, documentos, hallazgos, liquidaciones
from .storage import storage_por_defecto

app = FastAPI(title="Consorcio Transparente — API")
app.add_middleware(CORSMiddleware, allow_origins=[settings.cors_origin],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(consorcio.router)
app.include_router(documentos.router)
app.include_router(hallazgos.router)
app.include_router(liquidaciones.router)


@app.on_event("startup")
def arrancar():
    # Guarda de producción: sin R2 no hay deploy real, pero si hay R2 configurado
    # el secreto JWT por defecto es inaceptable (quedó en el historial de git).
    if settings.r2_endpoint and settings.jwt_secret == "solo-para-desarrollo":
        raise RuntimeError("CT_JWT_SECRET sin configurar: generar uno largo antes de desplegar")
    if settings.r2_endpoint and not settings.cookie_segura:
        raise RuntimeError("CT_COOKIE_SEGURA debe ser true en producción")
    Base.metadata.create_all(engine)  # Alembic llega con el primer deploy (Plan 3)
    if not hasattr(app.state, "storage"):
        app.state.storage = storage_por_defecto()


@app.get("/salud")
def salud():
    return {"ok": True}
