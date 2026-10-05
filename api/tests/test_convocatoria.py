from unittest.mock import MagicMock
from app import convocatoria
from app.convocatoria import normalizar_propuesta

OPC = ["A favor", "En contra", "Abstención"]

def test_normaliza_mociones_completas():
    crudo = {"metadatos": {"fecha": "3/09/26"},
             "agenda": [{"n": 1, "titulo": "Designación", "tipo": "procedimental"},
                        {"n": 3, "titulo": "Continuidad del encargado", "tipo": "deliberativo"}],
             "mociones": [{"titulo": "Que el encargado continúe"}]}
    out = normalizar_propuesta(crudo)
    assert out["mociones"][0]["titulo"] == "Que el encargado continúe"
    assert out["mociones"][0]["opciones"] == OPC
    assert out["mociones"][0]["regla"] == "abs"
    assert out["agenda"][1]["tipo"] == "deliberativo"

def test_descarta_mociones_sin_titulo():
    out = normalizar_propuesta({"mociones": [{"titulo": ""}, {"opciones": OPC}, {"titulo": "Válida"}]})
    assert [m["titulo"] for m in out["mociones"]] == ["Válida"]

def test_tolera_json_incompleto():
    out = normalizar_propuesta({})
    assert out["mociones"] == [] and out["agenda"] == [] and isinstance(out["metadatos"], dict)

def test_regla_invalida_cae_a_abs():
    out = normalizar_propuesta({"mociones": [{"titulo": "X", "regla": "cualquiera"}]})
    assert out["mociones"][0]["regla"] == "abs"


def _fake_claude(tool_input):
    msg = MagicMock()
    bloque = MagicMock(); bloque.type = "tool_use"; bloque.input = tool_input
    msg.content = [bloque]
    cli = MagicMock(); cli.messages.create.return_value = msg
    return cli

def test_proponer_mociones_usa_el_tool_output(monkeypatch):
    cli = _fake_claude({"metadatos": {"fecha": "3/09/26"},
                        "agenda": [{"n": 3, "titulo": "Encargado", "tipo": "deliberativo"}],
                        "mociones": [{"titulo": "Que continúe el encargado"}]})
    monkeypatch.setattr(convocatoria, "_cliente", lambda: cli)
    out = convocatoria.proponer_mociones(b"%PDF-1.4 ...", "conv.pdf")
    assert out["mociones"][0]["titulo"] == "Que continúe el encargado"
    assert out["mociones"][0]["opciones"] == ["A favor", "En contra", "Abstención"]
    _, kwargs = cli.messages.create.call_args
    assert kwargs["model"]


def test_endpoint_propone_con_token(cliente, monkeypatch):
    from app import convocatoria as conv
    monkeypatch.setattr(conv, "proponer_mociones",
                        lambda data, nombre: {"metadatos": {}, "agenda": [],
                                              "mociones": [{"titulo": "M", "opciones": ["A favor","En contra","Abstención"], "regla": "abs"}]})
    from app.config import settings
    monkeypatch.setattr(settings, "asamblea_token", "secreto")
    r = cliente.post("/asamblea/convocatoria",
                     files={"archivo": ("conv.pdf", b"%PDF-1.4 x", "application/pdf")},
                     headers={"X-Asamblea-Token": "secreto"})
    assert r.status_code == 200
    assert r.json()["mociones"][0]["titulo"] == "M"

def test_endpoint_sin_token_da_401(cliente, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "asamblea_token", "secreto")
    r = cliente.post("/asamblea/convocatoria",
                     files={"archivo": ("conv.pdf", b"x", "application/pdf")})
    assert r.status_code == 401

def test_endpoint_formato_no_soportado_da_400(cliente, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "asamblea_token", "secreto")
    r = cliente.post("/asamblea/convocatoria",
                     files={"archivo": ("conv.txt", b"x", "text/plain")},
                     headers={"X-Asamblea-Token": "secreto"})
    assert r.status_code == 400
