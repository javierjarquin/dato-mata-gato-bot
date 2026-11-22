"""Datos del guion contra el texto de sus fuentes (22/11/2026)."""

import json

from dato_mata_gato_bot import verificar_datos as vd


def test_numeros_en_palabras_y_en_cifras():
    valores = lambda t: [v for _, v in vd.numeros(t, 10)]  # noqa: E731
    assert valores("un hombre de setenta y dos años") == [72]
    assert valores("en mayo de dos mil veintiuno") == [2021]
    assert valores("cayó treinta y tres punto seis por ciento") == [33.6]   # "por ciento" no es 100
    assert valores("dos mil veinte doce punto tres") == [2020, 12.3]       # dos números, no 2032
    assert valores("tres mil trescientos un casos") == [3301]
    assert valores("dos millones de pesos") == [2_000_000]
    assert valores("millones de vistas") == []                            # sin número no es dato
    assert valores("3 mil 301 casos") == [3301]
    assert valores("283 mil pasajeros") == [283_000]
    assert 2400 in valores("2,400 panaderías")
    assert valores("dos hijos y tres días") == []                         # debajo del mínimo


def test_nombres_sin_mayusculas_de_pantalla_ni_arranques():
    texto = ("Según Noticaribe, Reyna González vivía en el Estado de México. EL CELULAR SONÓ ABAJO. "
             "Te imaginas a Richard Hart")
    assert vd.nombres(texto) == ["Reyna González", "Estado de México", "Richard Hart"]


def _guion():
    return {
        "planos": [
            {"id": "p01", "narracion": "Reyna González, de setenta y dos años, desapareció en dos mil veintiuno.",
             "texto_en_pantalla": "ATIZAPÁN · MAYO 2021"},
            {"id": "p02", "narracion": "Lo dijo Juan Pérez: «nunca vimos una cosa así en la colonia».",
             "texto_en_pantalla": ""},
        ],
        "evidencia": [
            {"id": "e1", "tipo": "prensa", "url": "https://nota/1", "fuente": "Nota"},
            {"id": "e2", "tipo": "prensa", "url": "https://muro/2", "fuente": "Con muro"},
            {"id": "f1", "tipo": "ficha", "titulo": "Lo que se sabe", "renglones": ["1,500 casos en 2020"]},
        ],
    }


def test_revisar_marca_lo_que_no_esta_en_las_fuentes(tmp_path):
    carpeta = tmp_path / "guion-x"
    carpeta.mkdir()
    (carpeta / "guion.json").write_text(json.dumps(_guion()), encoding="utf-8")
    paginas = {"https://nota/1": "La comerciante Reyna González, de 72 años, desapareció en mayo de 2021 "
                                 "en Atizapán. En 2020 hubo 1500 casos."}
    leidas = []

    def leer(url):
        leidas.append(url)
        return paginas.get(url)

    r = vd.revisar_slug("guion-x", entrada=tmp_path, leer=leer)
    faltan = {(d.tipo, d.texto) for d in r.sin_respaldo}
    assert ("nombre", "Juan Pérez") in faltan
    assert any(t == "cita" for t, _ in faltan)
    assert not any(t == "numero" for t, _ in faltan)          # 72, 2021, 1500 y 2020 están
    assert ("nombre", "Reyna González") not in faltan
    assert r.ilegibles == ["e2 (Con muro)"]
    resumen = r.resumen()
    assert "revisa antes de publicar" in resumen and "Juan Pérez" in resumen
    assert "no se dejaron leer" in resumen
    # El texto queda guardado: la segunda vez no se vuelve a bajar.
    vd.revisar_slug("guion-x", entrada=tmp_path, leer=leer)
    assert leidas == ["https://nota/1", "https://muro/2"]


def test_aviso_nunca_tumba_el_video(monkeypatch):
    monkeypatch.setattr(vd, "revisar_slug", lambda slug: (_ for _ in ()).throw(OSError("x")))
    assert vd.aviso("guion-x") == ""
