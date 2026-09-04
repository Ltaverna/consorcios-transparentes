import pathlib

import pytest

from app.db import Base, engine, SessionLocal

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "engine" / "tests" / "fixtures"


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)
