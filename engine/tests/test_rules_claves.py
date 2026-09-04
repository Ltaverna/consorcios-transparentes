import pathlib
import re

from ct.redconar import parse_text
from ct.rules import Config, evaluar

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def test_hallazgos_con_cifras_declaran_clave():
    """Un hallazgo cuyo título trae cifras (montos, porcentajes) no puede depender solo
    del título para su identidad entre reprocesos: necesita `clave` o `refs` estables."""
    for fx in ("redconar_202607.txt", "redconar_202608.txt"):
        liq = parse_text((FIXTURES / fx).read_text(encoding="utf-8"))
        for h in evaluar(liq, None, Config()):
            asume_estable = h.clave or h.refs
            assert asume_estable or not re.search(r"\d", h.titulo), f"{h.regla}: {h.titulo}"
