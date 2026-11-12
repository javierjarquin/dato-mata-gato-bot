"""Las escenas 3D que sustituyen al formato "noticia" (11/11/2026).

Lo que se prueba es lo que puede tumbar un video o publicar algo que no va:
que la revisión cache lo que el render no sabe dibujar, que el descarte deje
el video en pie, y que las animaciones de muerte y de armas no pasen.
"""

import json

import pytest

from dato_mata_gato_bot import escenas_3d, evidencia, instruccion_escenas

GUION = {
    "titulo": "Caso de prueba",
    "planos": [
        {"id": "p00", "seccion": "gancho_hablado", "narracion": "La patrulla llegó a las tres de la mañana."},
        {"id": "p01", "seccion": "contexto", "narracion": "Cuatro mujeres vivían en ese departamento."},
        {"id": "p02", "seccion": "identidad_cierre", "narracion": "Aquí el dato mata al gato.",
         "texto_en_pantalla": "DATO MATA GATO"},
    ],
    "evidencia": [{"id": "e1", "tipo": "prensa", "fuente": "Infobae, 11/11/2026"},
                  {"id": "f1", "tipo": "ficha", "titulo": "Una ficha"}],
}


def _plan(**cambios):
    plan = {
        "ambiente": "noche",
        "escenas": {
            "p00": {"visual": [{"objeto": "Suelo", "color": "#1C1F26"},
                               {"objeto": "Modelo", "modelo": "autos/police", "alto": 0.7}],
                    "camara": {"pos": [0, 1.3, 6], "mira": [0, 0.7, 0]},
                    "etiquetas": [{"titulo": "Colonia Narvarte", "desde": 0.1, "hasta": 0.6}],
                    "claves": ["patrulla"],
                    "evidencia": {"e": "e1", "desde": 0.2, "hasta": 0.5}},
            "p01": {"visual": [{"objeto": "Suelo"},
                               {"objeto": "Velas", "cantidad": 4, "posicion": [0, 0.7, 0]}],
                    "camara": "frente", "claves": ["mujeres"]},
        },
    }
    plan["escenas"]["p00"].update(cambios.pop("p00", {}))
    plan.update(cambios)
    return plan


def test_un_plan_bien_hecho_no_tiene_problemas():
    assert instruccion_escenas.problemas(_plan(), GUION) == []


def test_el_plano_de_cierre_no_necesita_escena():
    """Ahí va el cierre de marca del canal, que tapa la escena."""
    assert "p02" not in _plan()["escenas"]
    assert instruccion_escenas.problemas(_plan(), GUION) == []


def test_falta_un_plano():
    plan = _plan()
    del plan["escenas"]["p01"]
    assert any("p01" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_objeto_que_no_existe():
    plan = _plan(p00={"visual": [{"objeto": "Helicoptero"}]})
    assert any("Helicoptero" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_prop_que_no_existe():
    plan = _plan(p00={"visual": [{"objeto": "Suelo", "humo": 1}]})
    assert any("humo" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_modelo_que_no_esta_en_la_biblioteca():
    plan = _plan(p00={"visual": [{"objeto": "Modelo", "modelo": "autos/helicoptero"}]})
    assert any("helicoptero" in p for p in instruccion_escenas.problemas(plan, GUION))


@pytest.mark.parametrize("animacion", ["die", "attack-melee-right", "attack-kick-left", "holding-both-shoot"])
def test_ni_muerte_ni_armas(animacion):
    """La regla editorial la aguanta el código: esas animaciones existen en el
    modelo de Kenney y a propósito no están en el catálogo."""
    assert animacion not in instruccion_escenas.ANIMACIONES
    plan = _plan(p00={"visual": [{"objeto": "Personaje", "modelo": "personajes/character-male-a",
                                  "animacion": animacion}]})
    fallos = instruccion_escenas.problemas(plan, GUION)
    assert any("no reconstruimos" in p for p in fallos), fallos


def test_personaje_con_un_modelo_que_no_es_persona():
    plan = _plan(p00={"visual": [{"objeto": "Personaje", "modelo": "autos/police"}]})
    assert any("personajes/" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_camara_invalida():
    plan = _plan(p00={"camara": "dron"})
    assert any("camara" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_etiqueta_demasiado_larga():
    plan = _plan(p00={"etiquetas": [{"titulo": "T" * 40, "desde": 0.1, "hasta": 0.5}]})
    assert any("34 letras" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_clave_que_la_voz_no_dice():
    """El subtítulo resalta palabra por palabra: una clave que no se dice no
    se resalta nunca."""
    plan = _plan(p00={"claves": ["helicoptero"]})
    assert any("helicoptero" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_evidencia_que_no_es_del_guion():
    plan = _plan(p00={"evidencia": {"e": "e9"}})
    assert any("e9" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_nada_por_encima_de_la_franja_de_subtitulos():
    plan = _plan(p00={"visual": [{"objeto": "Modelo", "modelo": "autos/police", "posicion": [0, 9, 0]}]})
    assert any("y = 3" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_una_barda_delante_del_sujeto_tapa_el_cuadro():
    """El render escala por el ALTO: colonia/fence (0.48 x 0.27) con alto 1.4
    queda de 2.5 de ancho. En la primera corrida real fue una pared café que
    tapó el plano entero (11/11/2026)."""
    plan = _plan(p00={"visual": [{"objeto": "Modelo", "modelo": "colonia/fence", "alto": 1.4,
                                  "posicion": [0, 0, -0.4]}]})
    fallos = instruccion_escenas.problemas(plan, GUION)
    assert any("tapa el cuadro" in p for p in fallos), fallos


def test_la_misma_barda_al_fondo_si_va():
    plan = _plan(p00={"visual": [{"objeto": "Modelo", "modelo": "colonia/fence", "alto": 1.4,
                                  "posicion": [0, 0, -4.0]}]})
    assert not any("tapa el cuadro" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_una_calle_plana_no_tapa_nada():
    """Va con `ancho` y queda a ras de suelo: no estorba aunque sea ancha."""
    plan = _plan(p00={"visual": [{"objeto": "Modelo", "modelo": "calles/road-straight", "ancho": 2,
                                  "posicion": [0, 0, 0]}]})
    assert not any("tapa el cuadro" in p for p in instruccion_escenas.problemas(plan, GUION))


def test_el_catalogo_avisa_de_los_modelos_anchos():
    texto = instruccion_escenas.instruccion("guion-prueba", GUION)
    assert "colonia/fence (barda, ancho 1.8× su alto)" in texto


def test_un_sello_en_cada_plano_no():
    """El sello ocupa media pantalla: en todos los planos no deja ver la escena."""
    plan = _plan()
    for i, eid in enumerate(plan["escenas"]):
        plan["escenas"][eid]["evidencia"] = {"e": "e1"}
    GUION_LARGO = {**GUION, "planos": GUION["planos"] + [
        {"id": f"p{n}", "seccion": "contexto", "narracion": "Algo pasó aquí."} for n in range(10, 15)]}
    for n in range(10, 15):
        plan["escenas"][f"p{n}"] = {"visual": [{"objeto": "Suelo"}], "claves": ["algo"],
                                    "evidencia": {"e": "e1"}}
    fallos = instruccion_escenas.problemas(plan, GUION_LARGO)
    assert any("tope son 4" in p for p in fallos), fallos


def test_animacion_mal_hecha():
    plan = _plan(p00={"visual": [{"objeto": "Suelo", "escala": {"de": 0, "hasta": 2}}]})
    assert any("mal animado" in p for p in instruccion_escenas.problemas(plan, GUION))


# --- el descarte: un prop inventado no tumba un video --------------------------

def test_limpiar_tira_lo_que_no_existe_y_deja_lo_demas():
    plan = _plan(p00={"visual": [{"objeto": "Suelo", "color": "#111111", "humo": 1},
                                 {"objeto": "Helicoptero"},
                                 {"objeto": "Modelo", "modelo": "autos/police", "alto": 0.7}]})
    limpio, tirado = instruccion_escenas.limpiar(plan, GUION)
    visual = limpio["escenas"]["p00"]["visual"]
    assert [v["objeto"] for v in visual] == ["Suelo", "Modelo"]
    assert "humo" not in visual[0] and visual[0]["color"] == "#111111"
    assert any("Helicoptero" in t for t in tirado) and any("humo" in t for t in tirado)
    assert instruccion_escenas.problemas(limpio, GUION) == []


def test_limpiar_deja_una_escena_dibujable_aunque_todo_estuviera_mal():
    plan = {"ambiente": "marciano", "escenas": {"p00": {"visual": [{"objeto": "Nave"}], "camara": "dron"},
                                                "p01": {"visual": [{"objeto": "Suelo"}]}}}
    limpio, _ = instruccion_escenas.limpiar(plan, GUION)
    assert limpio["ambiente"] == "noche"
    assert limpio["escenas"]["p00"]["visual"] == [{"objeto": "Suelo"}]
    assert "camara" not in limpio["escenas"]["p00"]


def test_limpiar_aguanta_un_archivo_con_otra_forma():
    """Claude podría escribir una lista en vez de un diccionario: eso no puede
    reventar el paso, nada más deja al video sin escenas."""
    limpio, tirado = instruccion_escenas.limpiar({"escenas": [{"visual": []}]}, GUION)
    assert limpio["escenas"] == {} and tirado


def test_limpiar_tira_una_escena_que_no_es_de_ningun_plano():
    plan = _plan()
    plan["escenas"]["p99"] = {"visual": [{"objeto": "Suelo"}]}
    limpio, tirado = instruccion_escenas.limpiar(plan, GUION)
    assert "p99" not in limpio["escenas"] and any("p99" in t for t in tirado)


def test_resumen_visual_para_el_aviso_de_telegram():
    texto = instruccion_escenas.resumen_visual(_plan())
    assert "2 escenas" in texto and "1 sellos de evidencia" in texto


def test_la_instruccion_lleva_el_catalogo_y_el_guion():
    texto = instruccion_escenas.instruccion("guion-prueba", GUION)
    assert "autos/police" in texto and "La patrulla llegó" in texto
    assert "guion-prueba" in texto
    # El plano de cierre se nombra, pero pidiéndole que NO le haga escena.
    assert "p02 [identidad_cierre" in texto
    # Las piezas de evidencia sí; las fichas no son piezas que se puedan sellar.
    assert "e1 (prensa" in texto and "f1" not in texto


# --- el interruptor ------------------------------------------------------------

def _guion_en_disco(tmp_path, monkeypatch, guion):
    from dato_mata_gato_bot import pipeline

    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path)
    (tmp_path / "guion-x").mkdir()
    (tmp_path / "guion-x" / "guion.json").write_text(json.dumps(guion), encoding="utf-8")


def test_se_apaga_con_la_variable_de_entorno(tmp_path, monkeypatch):
    _guion_en_disco(tmp_path, monkeypatch, GUION)
    monkeypatch.setenv("ESCENAS_3D", "0")
    assert escenas_3d.usa_escenas("guion-x") is False


def test_se_apaga_en_un_guion_con_sin_escenas(tmp_path, monkeypatch):
    _guion_en_disco(tmp_path, monkeypatch, {**GUION, "plus": {"sin_escenas": True}})
    monkeypatch.delenv("ESCENAS_3D", raising=False)
    assert escenas_3d.usa_escenas("guion-x") is False


def test_por_defecto_va_con_escenas(tmp_path, monkeypatch):
    _guion_en_disco(tmp_path, monkeypatch, GUION)
    monkeypatch.delenv("ESCENAS_3D", raising=False)
    assert escenas_3d.usa_escenas("guion-x") is True


def test_tradiciones_no_pasa_por_aqui(tmp_path, monkeypatch):
    _guion_en_disco(tmp_path, monkeypatch, {**GUION, "formato": "tradiciones"})
    assert escenas_3d.usa_escenas("guion-x") is False


# --- las escenas con la IA gratis (12/11/2026) -----------------------------------

class _IA:
    """ia_gratis.pedir de mentira: contesta lo que se le da, en orden."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.prompts: list[str] = []

    def __call__(self, prompt, **_):
        from dato_mata_gato_bot import ia_gratis

        self.prompts.append(prompt)
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        ia_gratis._USADOS.add("gemini-de-prueba")
        return r


@pytest.fixture
def con_ia(tmp_path, monkeypatch):
    from dato_mata_gato_bot import ia_gratis

    _guion_en_disco(tmp_path, monkeypatch, GUION)
    monkeypatch.setenv("ESCENAS_MOTOR", "gratis")
    llamadas_claude = []
    monkeypatch.setattr(escenas_3d, "pedir_claude_json", lambda slug, guion, progreso=None:
                        llamadas_claude.append(slug) or escenas_3d.Escenas(True, "claude"))
    monkeypatch.setattr(escenas_3d, "pedir_claude", lambda slug, progreso=None:
                        llamadas_claude.append("herramientas") or escenas_3d.Escenas(True, "herramientas"))

    def poner(*respuestas):
        ia = _IA(*respuestas)
        monkeypatch.setattr(ia_gratis, "pedir", ia)
        return ia, llamadas_claude
    return poner


def test_la_instruccion_gratis_pide_el_json_y_no_herramientas():
    texto = instruccion_escenas.instruccion_json("guion-x", GUION)
    assert "CÓMO RESPONDER" in texto and "CÓMO TRABAJAR" not in texto
    assert "escenas.json" not in texto and "herramientas_guion" not in texto
    assert "CATÁLOGO" in texto and "p00" in texto


def test_gratis_a_la_primera_no_toca_claude(con_ia, tmp_path):
    ia, claude = con_ia(_plan())
    hechas = escenas_3d.pedir("guion-x")
    assert hechas.ok and "sin Claude (gemini-de-prueba)" in hechas.detalle
    assert claude == [] and len(ia.prompts) == 1
    assert json.loads((tmp_path / "guion-x" / "escenas.json").read_text(encoding="utf-8")) == _plan()


def test_gratis_corrige_con_la_lista_de_la_revision(con_ia):
    malo = _plan(p00={"visual": [{"objeto": "Suelo"}, {"objeto": "Helicoptero"}]})
    ia, claude = con_ia(malo, _plan())
    assert escenas_3d.pedir("guion-x").ok
    assert len(ia.prompts) == 2 and "Helicoptero" in ia.prompts[1] and "TU RESPUESTA ANTERIOR" in ia.prompts[1]
    assert claude == []


def test_si_la_ia_gratis_no_contesta_van_con_claude(con_ia):
    from dato_mata_gato_bot import ia_gratis

    _, claude = con_ia(ia_gratis.SinIA("Gemini: 429"))
    assert escenas_3d.pedir("guion-x").detalle == "claude"
    assert claude == ["guion-x"]


def test_si_queda_inservible_van_con_claude(con_ia):
    """Escenas que tras el descarte se quedan en puro Suelo no son un video."""
    inservible = {"ambiente": "noche", "escenas": {"p00": {"visual": [{"objeto": "Helicoptero"}]}}}
    _, claude = con_ia(*[inservible] * (escenas_3d.INTENTOS_GRATIS + 1))
    assert escenas_3d.pedir("guion-x").detalle == "claude"
    assert claude == ["guion-x"]


def test_lo_que_queda_mal_pero_sirve_se_limpia(con_ia, tmp_path):
    """Un prop inventado en la última vuelta no tumba el video: se descarta."""
    casi = _plan(p00={"visual": [{"objeto": "Suelo", "humo": 1}, {"objeto": "Modelo", "modelo": "autos/police"}]})
    _, claude = con_ia(*[casi] * (escenas_3d.INTENTOS_GRATIS + 1))
    hechas = escenas_3d.pedir("guion-x")
    assert hechas.ok and "se descartaron" in hechas.detalle and claude == []
    guardado = json.loads((tmp_path / "guion-x" / "escenas.json").read_text(encoding="utf-8"))
    assert "humo" not in guardado["escenas"]["p00"]["visual"][0]


@pytest.mark.parametrize("valor, esperado", [("claude", ["guion-x"]), ("", ["guion-x"]), ("otro", ["guion-x"]),
                                             ("claude_herramientas", ["herramientas"])])
def test_sin_motor_gratis_no_se_usa_la_ia_gratis(con_ia, monkeypatch, valor, esperado):
    ia, claude = con_ia()
    monkeypatch.setenv("ESCENAS_MOTOR", valor)
    escenas_3d.pedir("guion-x")
    assert ia.prompts == [] and claude == esperado


# --- Claude sin herramientas (12/11/2026) ----------------------------------------

@pytest.fixture
def con_claude(tmp_path, monkeypatch):
    from dato_mata_gato_bot import claude_runner, fabrica

    _guion_en_disco(tmp_path, monkeypatch, GUION)
    monkeypatch.setattr(fabrica, "tokens_de_sesiones", lambda s: {"total": 1000})

    def poner(*textos):
        llamadas = []

        def run_turn(sesion, mensaje, is_new_session, **kw):
            llamadas.append({"mensaje": mensaje, "nueva": is_new_session, **kw})
            t = textos[len(llamadas) - 1]
            return claude_runner.ClaudeTurnResult(ok=t is not None, text=t or "You've hit your session limit", raw="")
        monkeypatch.setattr(claude_runner, "run_turn", run_turn)
        return llamadas
    return poner


def test_claude_json_sin_herramientas_y_a_la_primera(con_claude, tmp_path):
    llamadas = con_claude("```json\n" + json.dumps(_plan()) + "\n```")
    hechas = escenas_3d.pedir_claude_json("guion-x", GUION)
    assert hechas.ok and "Claude sin herramientas" in hechas.detalle
    assert len(llamadas) == 1 and llamadas[0]["herramientas"] == "" and llamadas[0]["sistema"]
    assert json.loads((tmp_path / "guion-x" / "escenas.json").read_text(encoding="utf-8")) == _plan()


def test_claude_json_corrige_en_la_misma_sesion_solo_con_la_lista(con_claude):
    malo = _plan(p00={"visual": [{"objeto": "Suelo"}, {"objeto": "Helicoptero"}]})
    llamadas = con_claude(json.dumps(malo), "Aquí va:\n" + json.dumps(_plan()))
    assert escenas_3d.pedir_claude_json("guion-x", GUION).ok
    assert [l["nueva"] for l in llamadas] == [True, False]
    assert "Helicoptero" in llamadas[1]["mensaje"] and "CATÁLOGO" not in llamadas[1]["mensaje"]


def test_claude_json_sin_cuota_no_insiste(con_claude):
    llamadas = con_claude(None)
    hechas = escenas_3d.pedir_claude_json("guion-x", GUION)
    assert not hechas.ok and "limit" in hechas.detalle and len(llamadas) == 1


def test_claude_json_que_no_es_json(con_claude):
    con_claude(*["no sé"] * (escenas_3d.INTENTOS + 1))
    assert not escenas_3d.pedir_claude_json("guion-x", GUION).ok


# --- captcha en vez de la nota -------------------------------------------------

class _Pagina:
    def __init__(self, datos):
        self.datos = datos

    def evaluate(self, js):
        return self.datos


@pytest.mark.parametrize("datos", [
    {"titulo": "Just a moment...", "texto": "Enable JavaScript and cookies to continue", "largo": 60, "marcas": 0},
    {"titulo": "sociedadnoticias", "texto": "Confirm you are human", "largo": 40, "marcas": 0},
    {"titulo": "Verificación", "texto": "Verifica que eres humano", "largo": 50, "marcas": 0},
    {"titulo": "", "texto": "", "largo": 80, "marcas": 2},
])
def test_un_captcha_no_es_la_nota(datos):
    assert evidencia.pagina_bloqueada(_Pagina(datos))


def test_una_nota_de_verdad_pasa():
    assert evidencia.pagina_bloqueada(_Pagina(
        {"titulo": "Sindicato del Metro", "texto": "La Línea A lleva…", "largo": 6000, "marcas": 0})) == ""


def test_una_nota_que_habla_de_captchas_no_se_descarta():
    """El tope de largo está para esto: una nota sobre Cloudflare es una nota."""
    assert evidencia.pagina_bloqueada(_Pagina(
        {"titulo": "Cloudflare se cayó y tiró medio internet", "texto": "El captcha de Cloudflare…",
         "largo": 4200, "marcas": 1})) == ""


def test_si_la_pagina_no_se_puede_mirar_no_se_descarta():
    class _Rota:
        def evaluate(self, js):
            raise RuntimeError("navegador cerrado")

    assert evidencia.pagina_bloqueada(_Rota()) == ""
