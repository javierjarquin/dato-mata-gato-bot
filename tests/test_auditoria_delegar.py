"""Auditoría del 29/10/2026: lo que se le quitó a Claude (sin red ni IA real)."""

import json
from datetime import datetime, timedelta, timezone

from dato_mata_gato_bot import expediente, fabrica, herramientas_guion, ia_gratis

LARGA = ("La alcaldía dijo que el agua llegaría a todas las colonias del sur durante la semana "
         "pasada pero los vecinos de tres colonias siguen esperando la pipa desde el lunes temprano.")


def _guion_en(tmp_path, monkeypatch, slug, guion):
    monkeypatch.setattr(fabrica.pipeline, "ANDROID_IN", tmp_path)
    (tmp_path / slug).mkdir()
    (tmp_path / slug / "guion.json").write_text(json.dumps(guion, ensure_ascii=False), encoding="utf-8")
    return tmp_path / slug / "guion.json"


def test_revisar_no_trata_la_comparativa_como_polemica(tmp_path, monkeypatch):
    _guion_en(tmp_path, monkeypatch, "guion-comparativa-x", {"_schema": {"veredicto": {"mejor": "a"}}, "planos": []})
    monkeypatch.setattr(fabrica, "problemas_cercania", lambda slug: [])
    for f in ("problemas_de_forma", "problemas_de_evidencia", "problemas_de_plus"):
        monkeypatch.setattr(herramientas_guion, f, lambda g: [])
    salida = herramientas_guion.revisar("guion-comparativa-x")
    assert "comparacion" in salida and "estigma" not in salida and "prueba_del_ofensor" not in salida


def test_plano_nuevo_rechaza_lo_inventado(monkeypatch):
    texto = "¿Te ha pasado? " + LARGA
    for respuesta, vale in [
        ("¿Te ha pasado? La alcaldía dijo que el agua llegaría a todas las colonias del sur durante la semana. Pero los vecinos de tres colonias siguen esperando la pipa desde el lunes.", True),
        ("¿Te ha pasado? La alcaldía mintió: cinco colonias siguen sin agua.", False),   # palabras nuevas
        ("La alcaldía dijo que el agua llegaría. Tres colonias siguen esperando.", False),  # quitó la pregunta
        ("¿Te ha pasado? La alcaldía dijo que el agua llegaría a 3 colonias.", False)]:     # cifra con número
        monkeypatch.setattr(ia_gratis, "pedir", lambda *a, r=respuesta, **k: {"narracion": r})
        assert (herramientas_guion._plano_nuevo(texto, 25, "") is not None) is vale, respuesta


def test_revisar_arregla_lo_mecanico_y_si_no_pasa_deja_el_archivo(tmp_path, monkeypatch):
    largo = "Los vecinos de la colonia Centro esperan la pipa del agua desde el lunes y nadie les responde."
    corta = "Los vecinos de la colonia Centro esperan la pipa desde el lunes y nadie responde."
    doble = largo + " " + largo

    def guion(dobles):
        return {"planos": [{"id": "p00", "narracion": "El agua no llega a tu colonia."}]
                + [{"id": f"p0{i}", "narracion": doble if i in dobles else largo} for i in range(1, 9)]}
    ruta = _guion_en(tmp_path, monkeypatch, "guion-x", guion(range(1, 6)))

    def problemas(slug):
        return herramientas_guion.problemas_de_forma(json.loads(ruta.read_text(encoding="utf-8")))
    monkeypatch.setattr(herramientas_guion, "problemas", problemas)
    assert int(problemas("x")[0].split()[3]) > herramientas_guion.MAX_SOBRA
    # Muy largo: ni se intenta (recortar tanto es editar).
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía")))
    assert herramientas_guion.revisar("guion-x").startswith("Corrige TODO")

    ruta.write_text(json.dumps(guion({3, 4, 5}), ensure_ascii=False), encoding="utf-8")
    assert problemas("x") == ["la narración tiene 205 palabras; tienen que ser 120 a 190"]
    original = ruta.read_text(encoding="utf-8")
    monkeypatch.setattr(ia_gratis, "pedir",
                        lambda prompt, **k: {"narracion": corta + " " + corta if doble in prompt else corta})
    salida = herramientas_guion.revisar("guion-x")
    assert salida.startswith("OK") and "IA gratis" in salida

    # Si la IA mete algo nuevo, el archivo queda como estaba y Claude recibe el reporte.
    ruta.write_text(original, encoding="utf-8")
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {"narracion": "Inventé cosas nuevas aquí."})
    assert herramientas_guion.revisar("guion-x").startswith("Corrige TODO")
    assert ruta.read_text(encoding="utf-8") == original


def test_plano_nuevo_no_quita_cifras_ni_nombres(monkeypatch):
    texto = "El promedio en Baja California Sur es de seiscientos setenta pesos diarios, según el IMSS."
    for respuesta, vale in [("El promedio en Baja California Sur es de seiscientos setenta pesos diarios según el IMSS.", True),
                            ("El promedio en Baja California Sur es de setenta pesos diarios, según el IMSS.", False),
                            ("El promedio es de seiscientos setenta pesos diarios, según el IMSS.", False)]:
        monkeypatch.setattr(ia_gratis, "pedir", lambda *a, r=respuesta, **k: {"narracion": r})
        assert (herramientas_guion._plano_nuevo(texto, 14, "") is not None) is vale, respuesta


def test_revisar_no_toca_si_hay_algo_de_fondo(tmp_path, monkeypatch):
    ruta = _guion_en(tmp_path, monkeypatch, "guion-x", {"planos": []})
    monkeypatch.setattr(herramientas_guion, "problemas", lambda slug: [
        "la narración tiene 200 palabras; tienen que ser 120 a 190", "falta \"_schema.que_paso\""])
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía")))
    assert herramientas_guion.revisar("guion-x").startswith("Corrige TODO")
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"planos": []}


def test_buscar_sin_dato_da_lo_mas_cercano_literal(monkeypatch):
    texto = ("Relleno sin nada que ver. " * 50 + "\n\nLa tarifa del agua en Cancún subió 30 por ciento "
             "según Aguakan en octubre.\n\n" + "Más relleno. " * 50)
    monkeypatch.setattr(expediente, "leer", lambda liga, tope=None: texto)
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {"datos": []})
    salida = expediente.buscar("cuánto subió la tarifa del agua en Cancún", ["https://x.mx/n"])
    assert "lo más cercano" in salida and "subió 30 por ciento" in salida and len(salida) < 1200


def test_impacto_cuenta_medios_dias_y_tendencia():
    hoy = datetime.now(timezone.utc)
    cobertura = [{"medio": m, "fecha": hoy - timedelta(days=d)} for m, d in
                 [("Infobae", 0), ("Milenio", 1), ("Milenio", 1), ("PorEsto", 30)]]
    texto = expediente.impacto({"tendencia": "tendencia en X: #Agua"}, cobertura)
    assert texto.startswith("2 medios distintos") and "2 días distintos" in texto and "#Agua" in texto
    assert "PorEsto" not in texto  # de hace un mes no cuenta


def test_plano_nuevo_no_quita_la_atribucion(monkeypatch):
    texto = "Él dijo que entró antes de dos mil veintiuno; el IMSS, desde dos mil diecinueve."
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {
        "narracion": "Él entró antes de dos mil veintiuno; el IMSS, desde dos mil diecinueve."})
    assert herramientas_guion._plano_nuevo(texto, 13, "") is None
