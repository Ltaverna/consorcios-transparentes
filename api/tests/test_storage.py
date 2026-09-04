from app.storage import LocalStorage


def test_local_guardar_leer_y_url(tmp_path):
    st = LocalStorage(str(tmp_path))
    st.guardar("liquidaciones/2026-08.pdf", b"contenido")
    assert st.leer("liquidaciones/2026-08.pdf") == b"contenido"
    assert st.url_firmada("liquidaciones/2026-08.pdf") is None  # local: se sirve por streaming
    assert st.existe("liquidaciones/2026-08.pdf")
    assert not st.existe("no/esta.pdf")


def test_local_no_escapa_del_directorio(tmp_path):
    st = LocalStorage(str(tmp_path))
    try:
        st.leer("../fuera.txt")
        assert False, "debería rechazar rutas fuera del directorio"
    except ValueError:
        pass


def test_local_borrar(tmp_path):
    st = LocalStorage(str(tmp_path))
    st.guardar("informes/2026-08.html", b"contenido")
    assert st.existe("informes/2026-08.html")
    st.borrar("informes/2026-08.html")
    assert not st.existe("informes/2026-08.html")


def test_local_borrar_archivo_inexistente_no_falla(tmp_path):
    st = LocalStorage(str(tmp_path))
    st.borrar("informes/no-existe.html")  # no debe tirar excepción
