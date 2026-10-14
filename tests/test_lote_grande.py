"""Lotes grandes: reparto de formatos, rotación de avatares y archivado.

Un lote grande son once horas de máquina. Un error de reparto o de nombre no
se descubre hasta el final, así que conviene que estas reglas estén fijadas
por tests y no por la corrida.
"""

import json
from datetime import date
from pathlib import Path

from dato_mata_gato_bot import formatos, lote_grande


def test_el_lote_grande_reparte_entre_todos_los_formatos():
    """El punto del lote grande es que no sea todo crimen clásico."""
    tramos = formatos.repartir(30)
    claves = {c for c, _, _ in tramos}
    assert claves == {"crimen", "famoso", "abierto", "version_oficial",
                      "dato_15", "culpable", formatos.MITO}
    assert sum(c for _, _, c in tramos) == 30


def test_el_lote_grande_ya_no_trae_trivias():
    """El usuario las sacó el 28/09/2026; siguen con su comando propio."""
    for n in (5, 20, 30):
        assert formatos.TRIVIA not in {c for c, _, _ in formatos.repartir(n)}
    assert formatos.TRIVIA in {c for c, _, _ in formatos.repartir(30, con_trivia=True)}


def test_el_reparto_devuelve_exactamente_lo_pedido():
    for n in range(1, 60):
        assert sum(c for _, _, c in formatos.repartir(n)) == n


def test_el_reparto_es_determinista():
    """Una corrida cortada se tiene que poder repetir igual."""
    assert formatos.repartir(30) == formatos.repartir(30)


def test_un_lote_chico_no_se_dispersa():
    """Con 5 videos conviene el formato conocido, no uno de cada cosa."""
    tramos = dict((c, n) for c, _, n in formatos.repartir(5))
    assert tramos.get("crimen", 0) >= 1


def test_cada_formato_trae_su_instruccion_menos_el_clasico():
    for clave in ("famoso", "abierto", "version_oficial", "culpable", "dato_15"):
        assert formatos.instruccion_de(clave).strip(), clave
    # El clásico es la instrucción base sin agregados.
    assert formatos.instruccion_de("crimen") == ""


def _entrada(tmp_path, slugs_y_planos):
    """Carpeta de guiones falsa: {slug: cantidad de planos}."""
    for slug, n in slugs_y_planos.items():
        (tmp_path / slug).mkdir(parents=True, exist_ok=True)
        (tmp_path / slug / "guion.json").write_text(
            json.dumps({"planos": [{} for _ in range(n)]}), encoding="utf-8")
    return tmp_path


def test_los_avatares_rotan_y_no_se_repite_siempre_el_mismo(tmp_path, monkeypatch):
    monkeypatch.setattr(lote_grande.avatar_presentador,
                        "avatares_disponibles", lambda: [0, 1, 2])
    slugs = [f"guion-{i}" for i in range(30)]
    entrada = _entrada(tmp_path, {s: 8 for s in slugs})
    plan = lote_grande.planificar(slugs, entrada=entrada)
    usados = [a for _, a in plan.tareas if a is not None]
    # Uno de cada diez desde el 28/09/2026 (antes uno de cada cinco: 6).
    assert len(usados) == 3
    assert sorted(usados) == [0, 1, 2], usados


def test_el_presentador_no_va_a_una_trivia(tmp_path, monkeypatch):
    """En una trivia taparía las tarjetas de pregunta."""
    monkeypatch.setattr(lote_grande.avatar_presentador,
                        "avatares_disponibles", lambda: [0, 1, 2])
    slugs = [f"trivia-{i}" if i % 2 else f"guion-{i}" for i in range(30)]
    entrada = _entrada(tmp_path, {s: 8 for s in slugs})
    plan = lote_grande.planificar(slugs, entrada=entrada)
    con = [s for s, a in plan.tareas if a is not None]
    assert con and not any(s.startswith("trivia") for s in con), con


def test_el_presentador_no_va_a_un_video_de_quince_segundos(tmp_path, monkeypatch):
    """Media hora de GPU para un video de tres planos no se justifica.
    Pasó el 18/09/2026: el único avatar del lote le tocó al más corto."""
    monkeypatch.setattr(lote_grande.avatar_presentador,
                        "avatares_disponibles", lambda: [0])
    slugs = [f"guion-{i}" for i in range(10)]
    entrada = _entrada(tmp_path, {s: (3 if i < 5 else 8)
                                  for i, s in enumerate(slugs)})
    plan = lote_grande.planificar(slugs, entrada=entrada)
    con = [s for s, a in plan.tareas if a is not None]
    assert con and all(int(s.split("-")[1]) >= 5 for s in con), con


def test_sin_guion_legible_no_se_arriesga_media_hora(tmp_path):
    assert not lote_grande.admite_avatar("guion-fantasma", entrada=tmp_path)


def test_la_planificacion_es_determinista(tmp_path, monkeypatch):
    monkeypatch.setattr(lote_grande.avatar_presentador,
                        "avatares_disponibles", lambda: [0, 1, 2])
    slugs = [f"guion-{i}" for i in range(12)]
    entrada = _entrada(tmp_path, {s: 8 for s in slugs})
    assert (lote_grande.planificar(slugs, entrada=entrada).tareas
            == lote_grande.planificar(slugs, entrada=entrada).tareas)


def test_la_carpeta_lleva_la_fecha_del_lote():
    p = lote_grande.carpeta_del_dia(date(2026, 9, 18))
    assert p.name == "2026-09-18"


def test_se_archiva_con_el_nombre_corto_del_caso(tmp_path, monkeypatch):
    from dato_mata_gato_bot import pipeline
    proyecto = tmp_path / "proyectos" / "guion-largo-y-feo"
    proyecto.mkdir(parents=True)
    (proyecto / "guion.json").write_text(
        json.dumps({"titulo": "Villas de Salvárcar"}), encoding="utf-8")
    final = proyecto / "final.mp4"
    final.write_bytes(b"video")
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proyectos")

    destino = pipeline._archivar_local("guion-largo-y-feo", final, tmp_path / "lote")
    assert destino.name == "villasdesalvarcar.mp4"
    assert destino.read_bytes() == b"video"
    # El original no se toca: el archivado es una copia.
    assert final.exists()


def test_dos_casos_con_el_mismo_titulo_no_se_pisan(tmp_path, monkeypatch):
    from dato_mata_gato_bot import pipeline
    carpeta = tmp_path / "lote"
    for slug in ("guion-a", "guion-b"):
        proyecto = tmp_path / "proyectos" / slug
        proyecto.mkdir(parents=True)
        (proyecto / "guion.json").write_text(
            json.dumps({"titulo": "Caso Durazno"}), encoding="utf-8")
        (proyecto / "final.mp4").write_bytes(slug.encode())
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proyectos")

    p1 = pipeline._archivar_local("guion-a", tmp_path/"proyectos"/"guion-a"/"final.mp4", carpeta)
    p2 = pipeline._archivar_local("guion-b", tmp_path/"proyectos"/"guion-b"/"final.mp4", carpeta)
    assert p1.name == "casodurazno.mp4"
    assert p2.name == "casodurazno_2.mp4"
    assert p1.read_bytes() == b"guion-a"
    assert p2.read_bytes() == b"guion-b"


def test_ningun_formato_pide_la_segunda_persona_vieja():
    """La fórmula cambió el 20/09/2026: "Te imaginas a..." en tercera persona.

    Los formatos se escribieron cuando el p01 abría con "Eres...", y si alguno
    sigue diciéndolo, ese tramo del lote sale con la fórmula vieja y el canal
    queda mezclando dos estilos.
    """
    for clave, formato in formatos.FORMATOS.items():
        texto = formato.instruccion
        assert '"Eres' not in texto, f"{clave} todavía pide la fórmula vieja"


def test_los_formatos_con_contexto_remiten_a_la_formula():
    """Salvo el de 15 segundos, que no tiene plano de contexto."""
    assert "Te imaginas" in formatos.instruccion_de("famoso")
    assert "Te imaginas" in formatos.instruccion_de("dato_15")  # para decir que NO aplica
