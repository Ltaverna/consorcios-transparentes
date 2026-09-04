"""Parseo del portal de Redconar sin red (HTML mínimo con la misma estructura)."""
from ct.portal import parse_tabla_egresos, parse_adjuntos, opciones_select, etiqueta_mes, nombre_archivo

TABLA = """<html><select id="periodSelectGasto"><option value="2026-8" selected>Agosto 2026</option><option value="2026-7">Julio 2026</option></select>
<select id="categorySelectGasto"><option value="all">Todas</option></select>
<table id="exampleGasto"><thead><tr><th>Fecha</th></tr></thead><tbody>
<tr><td>01-08-2026</td><td>POR ARREGLO<br>CAMARAS</td><td>$ 70,000.00</td><td>$ 70,000.00 - CAJA</td><td>00001-00000005</td><td>KEVIN LUCAS AVALOS</td><td>GASTOS GENERALES</td>
<td><a onclick="Attachments.attachList_outflow('35868754','Egreso','no_delete','5308904','Ticket','0', '1');">x</a></td></tr>
<tr><td>04-08-2026</td><td>Sueldo &amp; cargas</td><td>$ 1,424,799.00</td><td>$ 1,424,799.00 - BANCO</td><td></td><td>Consorcio RIVADAVIA 2069</td><td>SUELDOS</td>
<td><a onclick="Attachments.attachList_outflow('35797852','Egreso','no_delete','','Ticket','0', '1');">x</a></td></tr>
<tr><td></td><td>fila vacía</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
</tbody></table></html>"""

ADJ = """<script>var x='<span>no</span>';</script><table><tr><td><span>1786543136.7252FC Nº5 KEVIN.pdf</span></td>
<td><a href='https://redconar.net/viewers/attachViewer.php?id_attach=2649488&amp;type=Ticket&amp;token=abc&amp;no_download=1'><img src=eye.png></a></td></tr></table>"""


def test_tabla():
    e = parse_tabla_egresos(TABLA)
    assert len(e) == 2
    assert e[0].n == 1 and e[0].proveedor == "KEVIN LUCAS AVALOS" and e[0].desc == "POR ARREGLO CAMARAS"
    assert e[0].id_egreso == "35868754" and e[0].id_ticket == "5308904"
    assert e[1].id_ticket is None and e[1].desc == "Sueldo & cargas"


def test_selects_y_adjuntos():
    assert opciones_select(TABLA, "periodSelectGasto") == [("2026-8", "Agosto 2026"), ("2026-7", "Julio 2026")]
    a = parse_adjuntos(ADJ)
    assert len(a) == 1 and a[0].nombre.startswith("1786543136") and "&type=Ticket" in a[0].url


def test_nombres():
    assert etiqueta_mes("2026-7") == "2026-07 Julio"
    e = parse_tabla_egresos(TABLA)[0]
    assert nombre_archivo(e, 1, "Ticket", "1786543136.7252FC Nº5 KEVIN.pdf", ".pdf") == "01-1 01-08-2026 KEVIN LUCAS AVALOS 70,000.00 T 1786543136.7252FC No5 KEVIN.pdf"
