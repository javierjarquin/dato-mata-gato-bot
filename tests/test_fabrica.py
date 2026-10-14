import json
from datetime import datetime

import pytest

from dato_mata_gato_bot import fabrica, lote_grande


@pytest.fixture
def fab(tmp_path, monkeypatch):
    monkeypatch.setattr(fabrica, "RAIZ", tmp_path / "fabrica")
    monkeypatch.setattr(fabrica.pipeline, "ANDROID_IN", tmp_path)
    monkeypatch.setattr(fabrica, "asegurar_infra", lambda: None)
    monkeypatch.setattr(fabrica, "disco_libre_gb", lambda: 200.0)
    monkeypatch.setattr(fabrica, "telegram", lambda *a, **k: None)
    monkeypatch.setattr(fabrica, "tokens_de_sesiones", lambda ids: {"total": 0})
    monkeypatch.setattr(lote_grande, "repartir_voces", lambda plan: {})
    monkeypatch.delenv("FABRICA_HORAS_CLAUDE", raising=False)
    monkeypatch.setenv("FABRICA_TANDAS_5H", "99")
    return tmp_path


def _escritor(monkeypatch, tandas):
    """Cada llamada devuelve la siguiente tanda: (slugs, aviso_de_cuota)."""
    llamadas = iter(tandas)

    def escribir(estado):
        estado.setdefault("_sesiones_tanda", [])
        return next(llamadas)
    monkeypatch.setattr(fabrica, "escribir_tanda", escribir)


def test_hora_de_reset_lee_la_hora_del_aviso():
    ahora = datetime(2026, 10, 12, 14, 0)
    assert fabrica.hora_de_reset("You've hit your session limit · resets 3:40pm", ahora) == \
        datetime(2026, 10, 12, 15, 42)
    assert fabrica.hora_de_reset("resets 1am", ahora) == datetime(2026, 10, 13, 1, 2)
    sin_hora = fabrica.hora_de_reset("límite raro", ahora)
    assert (sin_hora - ahora).total_seconds() == fabrica.ESPERA_CUOTA


def test_un_fallido_se_reintenta_una_vez_al_final_de_la_fila(fab, monkeypatch):
    fabrica.crear("t", 3)
    _escritor(monkeypatch, [(["guion-a", "guion-b", "guion-c"], None)])
    resultados = {"guion-a": [False, True], "guion-b": [True], "guion-c": [True]}
    orden = []

    def correr(lote, slug):
        orden.append(slug)
        return resultados[slug].pop(0), "x"
    monkeypatch.setattr(fabrica, "_correr_video", correr)

    assert fabrica.ciclo("t") == "terminado"
    assert orden == ["guion-a", "guion-b", "guion-c", "guion-a"]
    estado = fabrica.leer("t")
    assert {s: v["estado"] for s, v in estado["videos"].items()} == \
        {"guion-a": "listo", "guion-b": "listo", "guion-c": "listo"}


def test_dos_fallos_lo_dejan_fuera_y_la_fabrica_termina(fab, monkeypatch):
    fabrica.crear("t", 1)
    _escritor(monkeypatch, [(["guion-a"], None)])
    monkeypatch.setattr(fabrica, "_correr_video", lambda lote, slug: (False, "roto"))
    assert fabrica.ciclo("t") == "terminado"
    v = fabrica.leer("t")["videos"]["guion-a"]
    assert v["estado"] == "fallido" and v["intentos"] == 2


def test_sin_cuota_sigue_renderizando_y_guarda_lo_ya_escrito(fab, monkeypatch):
    fabrica.crear("t", 10)
    _escritor(monkeypatch, [(["guion-a"], "You've hit your session limit · resets 11:00pm")])
    monkeypatch.setattr(fabrica, "_correr_video", lambda lote, slug: (True, "ok"))
    motivo = fabrica.ciclo("t")
    estado = fabrica.leer("t")
    assert estado["videos"]["guion-a"]["estado"] == "listo"   # lo escrito antes del corte no se pierde
    assert estado["cuota_libre_desde"] is not None
    assert motivo == "esperando la cuota de Claude para escribir más guiones"


def test_un_corte_a_mitad_se_retoma_desde_el_estado(fab, monkeypatch):
    fabrica.crear("t", 2)
    _escritor(monkeypatch, [(["guion-a", "guion-b"], None)])

    def se_corta(lote, slug):
        raise KeyboardInterrupt  # como si Windows se reiniciara a mitad del primer video
    monkeypatch.setattr(fabrica, "_correr_video", se_corta)
    with pytest.raises(KeyboardInterrupt):
        fabrica.ciclo("t")
    assert not (fabrica.RAIZ / "t" / "latido.json").exists()

    hechos = []
    monkeypatch.setattr(fabrica, "_correr_video", lambda lote, slug: (hechos.append(slug), (True, "ok"))[1])
    assert fabrica.ciclo("t") == "terminado"
    assert hechos == ["guion-a", "guion-b"]   # no se pidieron guiones de nuevo, no se saltó ninguno


def test_no_corren_dos_ciclos_a_la_vez(fab, monkeypatch):
    fabrica.crear("t", 1)
    monkeypatch.setattr(fabrica, "_proceso_vivo", lambda pid: True)
    (fabrica.RAIZ / "t" / "latido.json").write_text(
        json.dumps({"pid": -1, "t": __import__("time").time()}), encoding="utf-8")
    assert fabrica.ciclo("t") == "ya hay un ciclo corriendo"


def test_un_latido_fresco_de_un_proceso_muerto_se_retoma_ya(fab, monkeypatch):
    # Prueba de corte real del 12/10/2026: se mató el ciclo y el latido quedó fresco.
    fabrica.crear("t", 1)
    (fabrica.RAIZ / "t" / "latido.json").write_text(
        json.dumps({"pid": 999999, "t": __import__("time").time()}), encoding="utf-8")
    assert fabrica.tomar_latido("t")


def test_proceso_vivo_reconoce_al_propio():
    import os
    assert fabrica._proceso_vivo(os.getpid())
    assert not fabrica._proceso_vivo(999999)


def test_un_latido_viejo_se_considera_muerto(fab, monkeypatch):
    fabrica.crear("t", 1)
    (fabrica.RAIZ / "t" / "latido.json").write_text(json.dumps({"pid": -1, "t": 0}), encoding="utf-8")
    assert fabrica.tomar_latido("t")


def test_presupuesto_de_tandas_y_horario(monkeypatch):
    ahora = datetime(2026, 10, 12, 14, 0)
    estado = {"consumo": [{"t": "2026-10-12T12:00"}]}
    monkeypatch.setenv("FABRICA_TANDAS_5H", "1")
    monkeypatch.delenv("FABRICA_HORAS_CLAUDE", raising=False)
    assert "máximo 1" in fabrica.puede_usar_claude(estado, ahora)
    assert fabrica.puede_usar_claude(estado, datetime(2026, 10, 12, 17, 30)) is None
    monkeypatch.setenv("FABRICA_HORAS_CLAUDE", "0-9")
    assert "horario" in fabrica.puede_usar_claude({}, ahora)
    assert fabrica.puede_usar_claude({}, datetime(2026, 10, 12, 3, 0)) is None
    monkeypatch.setenv("FABRICA_HORAS_CLAUDE", "22-6")
    assert fabrica.puede_usar_claude({}, datetime(2026, 10, 12, 23, 0)) is None
    assert fabrica.puede_usar_claude({}, datetime(2026, 10, 12, 5, 0)) is None
    assert "horario" in fabrica.puede_usar_claude({}, datetime(2026, 10, 12, 12, 0))


def test_poco_disco_pausa_la_fabrica(fab, monkeypatch):
    fabrica.crear("t", 5)
    monkeypatch.setattr(fabrica, "disco_libre_gb", lambda: 5.0)
    assert "GB libres" in fabrica.ciclo("t")


def _guion_cercania(tmp_path, slug, condiciones):
    from dato_mata_gato_bot import fabrica as f
    (tmp_path / slug).mkdir()
    (tmp_path / slug / "guion.json").write_text(json.dumps({
        "_schema": {"condiciones": condiciones},
        "evidencia": [{"id": "e1", "tipo": "prensa"}, {"id": "e2", "tipo": "lugar"},
                      {"id": "e3", "tipo": "documento"}],
        "planos": [{"id": "p00", "narracion": "Si vives en Cancún pagas más.", "visual": {"evidencia": ["e1"]}},
                   {"id": "p08", "seccion": "identidad_cierre", "narracion": "Aquí el dato mata al gato.",
                    "visual": {}}]}), encoding="utf-8")
    return f.problemas_cercania(slug)


def test_cercania_exige_las_cuatro_condiciones_pero_no_tres_nombres(fab):
    completas = {c: "sí" for c in fabrica.CONDICIONES}
    assert _guion_cercania(fab, "guion-cancun-a", completas) == []
    sin_una = dict(completas, **{"4_coraje": ""})
    p = _guion_cercania(fab, "guion-cancun-b", sin_una)
    assert len(p) == 1 and "4_coraje" in p[0]


def test_reparto_de_temas_parejo_en_el_lote():
    from dato_mata_gato_bot import instruccion_cercania as ic
    total = {}
    for _ in range(10):  # 10 tandas de 10 = 100 guiones
        for clave, n in ic.repartir(10, total):
            total[clave] = total.get(clave, 0) + n
    assert sum(total.values()) == 100 and set(total.values()) == {20}
    # Tras un corte, la tanda siguiente va a los temas que se quedaron atrás.
    assert dict(ic.repartir(3, {"cancun": 2, "cdmx": 1})) == {"terror": 1, "historia": 1, "marfil": 1}
    assert ic.tema_de("guion-cdmx-socavones-hundimiento") == "cdmx"
    assert ic.tema_de("guion-tt-ed-gein") is None
    texto = ic.instruccion("cancun", 3, "Caso X")
    for frase in ("TE AFECTA", "ESTÁ PASANDO AHORITA", "ALGO NO CUADRA", "CORAJE",
                  "SE PUEDE GRABAR", "MÁXIMO 12 PALABRAS", "Caso X", "guion-cancun-"):
        assert frase in texto
