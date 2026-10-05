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
