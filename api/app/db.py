from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings


class Base(DeclarativeBase):
    pass


def _fk_on(dbapi_con, _):
    dbapi_con.execute("PRAGMA foreign_keys=ON")


def _crear_engine(url: str):
    if url.startswith("sqlite"):
        eng = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
        event.listens_for(eng, "connect")(_fk_on)
        return eng
    return create_engine(url, pool_pre_ping=True)


engine = _crear_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
