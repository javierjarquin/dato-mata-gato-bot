"""El formato de mitos y leyendas, integrado al bot (25/09/2026).

Sale de dos POC aprobados (mito-yum-balam, mito-huay-chivo). Cada test fija
algo que en esos POC salió mal o que es fácil romper sin darse cuenta.
"""

import ast
import json
import re
import unicodedata
from pathlib import Path

import pytest

from dato_mata_gato_bot import bot, formatos, lote_grande, pipeline, sessions

TAXONOMIA = Path(r"C:\illustrated-narrator\src\illustrated_narrator\domain\services\sfx_taxonomy.py")

# Lo que la instrucción le dice a Claude que puede pedir en audio.sfx.
SONIDOS_ANUNCIADOS = [
    "grillos", "monte", "selva", "viento", "lluvia", "latido", "olas", "fuego", "retumbo",
    "silbido", "chiflido", "pájaros", "ramas", "hojas", "pasos", "tecolote", "lechuza",
    "aullido", "llanto", "lamento", "respiración",
]


def _pelar(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto)
                   if not unicodedata.combining(c)).lower()


# ------------------------------------------------------------ el lote grande

def test_el_lote_grande_incluye_mitos():
    claves = {c for c, _, _ in formatos.repartir(30)}
    assert formatos.MITO in claves


def test_un_lote_chico_no_lleva_mitos():
    """Cada mito dura el doble que un video de crimen: en un lote de 5 no
    tienen lugar, y el canal sigue con lo que ya le funciona."""
    assert formatos.MITO not in {c for c, _, _ in formatos.repartir(5)}


def test_un_mito_no_lleva_presentador(tmp_path):
    """Dura unos 2:15 (casi una hora de MuseTalk) y taparía la dramatización."""
    (tmp_path / "mito-x").mkdir()
    (tmp_path / "mito-x" / "guion.json").write_text(
        json.dumps({"planos": [{} for _ in range(20)]}), encoding="utf-8")
    assert not lote_grande.admite_avatar("mito-x", entrada=tmp_path)


# --------------------------------------------------------------- el comando

def test_el_comando_mitos_esta_registrado():
    assert "mitos" in {n for n, _ in bot.BOT_COMMANDS}
    assert callable(bot.cmd_mitos)
    assert "/mitos" in bot.HELP_TEXT


# ------------------------------------------------------------ la instrucción

def test_la_instruccion_se_arma_con_la_cantidad():
    texto = bot.INSTRUCCION_MITO.format(n=3)
    assert "Genera 3 guiones" in texto
    assert '"guiones"' in texto  # el bloque que parsea _parse_lote_response


@pytest.mark.parametrize("regla", [
    '"formato": "mito"',          # sin esto el pipeline trae mapas por nombre
    "pausa_despues_seg",          # sin pausa, el sonido queda debajo de la voz
    '"personaje": true',          # si no, el ser de la leyenda nunca sale
    "NUNCA voseo",
    "NO mezcles leyendas",
    "Silbón",                     # el ejemplo real de mezcla
    "se salta",                   # otros países y lado oscuro son opcionales
    "\"eyes\"",                   # arrastra una cara
    "NO PUEDE CONTRADECIR LA NARRACIÓN",  # la mano de cinco dedos de la Xtabay
])
def test_la_instruccion_lleva_las_reglas_de_los_poc(regla):
    assert regla in bot.INSTRUCCION_MITO


def test_la_instruccion_de_mitos_no_esta_escrita_en_voseo():
    """La de crimen está en voseo y se contagió al guion: el lote del 22/09
    salió con "Decímelo" en los 20 cierres. Se saca el ejemplo de lo que NO
    hay que hacer, que sí nombra formas en voseo a propósito."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from medir_tono import VOSEO
    texto = re.sub(r"NUNCA voseo \([^)]*\)", "", bot.INSTRUCCION_MITO)
    assert not VOSEO.findall(texto), VOSEO.findall(texto)


@pytest.mark.skipif(not TAXONOMIA.exists(), reason="sin el repo de illustrated-narrator")
def test_cada_sonido_que_anuncia_la_instruccion_existe_en_el_narrador():
    """Si la instrucción ofrece un sonido que el narrador no conoce, el guion
    lo pide y el video sale mudo justo en la pausa de la señal -- que es el
    momento que el formato existe para crear."""
    arbol = ast.parse(TAXONOMIA.read_text(encoding="utf-8"))
    claves = next(
        [_pelar(k.value) for k in nodo.value.keys]
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Assign)
        and any(getattr(t, "id", "") == "SFX_KEYWORDS" for t in nodo.targets)
    )
    for palabra in SONIDOS_ANUNCIADOS:
        assert palabra in bot.INSTRUCCION_MITO, f"'{palabra}' ya no está en la instrucción"
        assert any(_pelar(palabra).startswith(c) for c in claves), \
            f"'{palabra}' no suena: el narrador no lo conoce"


# ----------------------------------------------------- red de seguridad

def test_si_claude_olvida_el_formato_el_bot_lo_pone(tmp_path):
    (tmp_path / "mito-a").mkdir()
    (tmp_path / "mito-a" / "guion.json").write_text(json.dumps({"planos": []}), encoding="utf-8")
    (tmp_path / "mito-b").mkdir()
    (tmp_path / "mito-b" / "guion.json").write_text(
        json.dumps({"formato": "mito", "planos": []}), encoding="utf-8")

    corregidos = bot._asegurar_formato_mito(["mito-a", "mito-b", None], entrada=tmp_path)

    assert corregidos == ["mito-a"]
    assert json.loads((tmp_path / "mito-a" / "guion.json").read_text(encoding="utf-8"))["formato"] == "mito"


# ------------------------------------------------------- cierre y revisión

def test_un_mito_cierra_con_su_propio_cartel(tmp_path, monkeypatch):
    """El del canal dice "¿QUÉ OPINAS DE ESTE CASO?": una leyenda no es un caso."""
    (tmp_path / "dato_mata_gato_cierre.jpg").write_bytes(b"canal")
    (tmp_path / "dato_mata_gato_cierre_mito.png").write_bytes(b"mito")
    monkeypatch.setattr(sessions, "LOGO_DIR", tmp_path)
    guion = {"formato": "mito", "planos": [{"id": "p20", "seccion": "identidad_cierre"}]}
    proyecto = tmp_path / "proyecto"

    pipeline._apply_cierre(proyecto, guion)

    elegidos = list((proyecto / "media" / "p20").glob("elegido*"))
    assert [e.read_bytes() for e in elegidos] == [b"mito"]


def test_un_video_de_crimen_sigue_con_el_cartel_de_siempre(tmp_path, monkeypatch):
    (tmp_path / "dato_mata_gato_cierre.jpg").write_bytes(b"canal")
    (tmp_path / "dato_mata_gato_cierre_mito.png").write_bytes(b"mito")
    monkeypatch.setattr(sessions, "LOGO_DIR", tmp_path)
    guion = {"planos": [{"id": "p07", "seccion": "identidad_cierre"}]}
    proyecto = tmp_path / "proyecto"

    pipeline._apply_cierre(proyecto, guion)

    assert [e.read_bytes() for e in (proyecto / "media" / "p07").glob("elegido*")] == [b"canal"]


def test_la_hoja_de_contacto_es_solo_para_mitos(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path)
    for slug, formato in (("mito-x", "mito"), ("guion-x", None)):
        (tmp_path / slug / "images").mkdir(parents=True)
        (tmp_path / slug / "guion.json").write_text(json.dumps(
            {"formato": formato, "planos": [{"id": "p09", "seccion": "identidad_cierre"}]}),
            encoding="utf-8")
        for nombre in ("p00_1", "p01_1", "p09_1"):
            Image.new("RGB", (448, 256), "gray").save(tmp_path / slug / "images" / f"{nombre}.png")

    assert pipeline.hoja_de_contacto("guion-x") is None
    hoja = pipeline.hoja_de_contacto("mito-x")
    assert hoja is not None and hoja.exists()


def test_la_pausa_se_lee_igual_en_el_plano_o_dentro_de_audio():
    """Claude la puso dentro de "audio" en los dos mitos del 26/09/2026. Si
    el audio y los tiempos de los planos leyeran distinto, los subtítulos
    quedarían corridos por toda la duración de la pausa."""
    from dato_mata_gato_bot import quiz_cards
    en_plano = {"id": "p01", "pausa_despues_seg": 1.8}
    en_audio = {"id": "p01", "audio": {"pausa_despues_seg": 1.8}}
    for plano in (en_plano, en_audio):
        assert pipeline._pausa_despues_seg(plano) == 1.8
        assert quiz_cards._pausa_de(plano) == 1.8
    assert pipeline._pausa_despues_seg({"id": "p02"}) == 0.0
