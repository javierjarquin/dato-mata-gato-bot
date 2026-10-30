"""Fórmula de LA POLÉMICA (17/10/2026).

Nace de comparar dos virales: el del agua de Yucatán, donde la disputa es sobre
un HECHO y existe un papel que la cerraría (el contrato Conagua-Mekorot), y el
del Conalep, donde lo que detonó todo fue una OPINIÓN ("son bandidazos") y
ningún documento decide si fue justa. Javier: "es una opinión lo que generó la
polémica, entonces no hay una fuente de la verdad, más bien la causa y la
respuesta de los afectados o la opinión pública tiene más sentido".
"""

import json

import pytest

from dato_mata_gato_bot import instruccion_polemica, instruccion_viral, revision_guion


def _base() -> dict:
    """Un guion de polémica que pasa todas las revisiones de la fórmula."""
    return {
        "_schema": {
            "que_paso": "Un podcast les dijo bandidazos a quienes estudian en el Conalep.",
            "por_que_esta_formula": "Ningún papel dice si el insulto fue justo: es una opinión.",
            "estigma": "Que ahí las muchachas se embarazan y que son los que asaltan.",
            "premisas": [
                {"dice": "que ahí las muchachas salen embarazadas",
                 "fuente_del_rumor": "estudio_estigma",
                 "dato": "Tres por ciento de las que siguen en la escuela estuvieron "
                         "embarazadas, contra treinta y nueve de las que ya no.",
                 "fuente_del_dato": "encuesta_oficial"},
                {"dice": "que son los que asaltan",
                 "fuente_del_rumor": "estudio_estigma",
                 "dato": "Nadie mide cuántos asaltan por escuela: seis de cada diez "
                         "adolescentes internados no llegaron a la prepa.",
                 "fuente_del_dato": "censo_oficial"},
            ],
            "prueba_del_ofensor": "Tres contra treinta y nueve no es una tasa de éxito de nadie.",
            "quien_fabrico_el_estigma": "Un decreto de 1978 la hizo terminal (decreto_dof)",
            "no_es_chisme": "El ofendido no es una persona: son 324,335 estudiantes.",
            "lo_que_sigue_sin_contestar": "La disculpa no toca el decreto de 1978.",
            "frase": {"texto": "bandidazos", "quien": "el podcast Los Parrilleros",
                      "donde": "TikTok", "cuando": "16/10/2026"},
            "reaccion": {
                "quien": "Ximena, de 18 años, alumna de mantenimiento automotriz",
                "cita": "Mi mamá se friega trabajando para pagarme el camión al plantel",
                "numeros": "más de 800 mil vistas en TikTok, 16/10/2026",
                "se_sumaron": ["la cuenta oficial de Conalep Nuevo León"],
                "respuesta_del_senalado": "Se disculparon el 17/10/2026: nos equivocamos.",
                "no_contestaron": ["la autoridad educativa federal, al 17/10/2026"]},
            "veredicto": {"pregunta": "¿Fue humor o fue discriminación?",
                          "lados": ["humor: era un podcast de comedia",
                                    "discriminación: lo dijeron de menores de edad"]},
            "condiciones": {c: "x" for c in instruccion_polemica.CONDICIONES},
            "preguntas_abiertas": ["¿Fue una broma que se les fue de las manos?",
                                   "¿O era el prejuicio de siempre, dicho con micrófono?"],
            "senalados": ["Conalep", "Ximena"],
            "hallado_en": "TikTok, @weraa_zx, 800 mil vistas, 16/10/2026",
            # Claves sin palabras del tema: una clave como "anuario_conalep"
            # metía "conalep" en cualquier frase que la citara y los candados se
            # cumplían con la cita (17/10/2026).
            "fuentes": {"estudio_estigma": "https://www.scielo.org.mx/estigma.php",
                        "encuesta_oficial": "https://www.inegi.org.mx/embarazos.pdf",
                        "censo_oficial": "https://www.inegi.org.mx/epacol.pdf",
                        "decreto_dof": "https://www.conalep.edu.mx/decreto.pdf"},
            "verificacion_final": {
                "datos": ["ochocientas mil vistas -- encuesta_oficial",
                          "tres por ciento contra treinta y nueve -- encuesta_oficial",
                          "seis de cada diez -- censo_oficial",
                          "mil novecientos setenta y ocho -- decreto_dof"],
                "misma_historia": "Arranca en el insulto y el dato contesta la premisa.",
                "corregido": "nada"},
        },
        "evidencia": [{"tipo": "red_social"}, {"tipo": "red_social"}, {"tipo": "documento"}],
        "plus": {"sin_nota_animada": ["p00", "p01", "p02"]},
        "planos": [
            {"id": "p00", "narracion": "Un podcast les dijo bandidazos al Conalep."},
            {"id": "p01", "narracion": "Te imaginas a quien estudia ahí. ¿A ti también te lo dijeron?"},
            {"id": "p02", "narracion": "Ximena contestó: mi mamá se friega trabajando para "
                                       "pagarme el camión al plantel."},
            {"id": "p03", "narracion": "Se dice que ahí las muchachas salen embarazadas. Tres "
                                       "por ciento de las que siguen en la escuela. ¿Tú lo sabías?"},
            {"id": "p04", "narracion": "¿Y que son los que asaltan? Seis de cada diez internados "
                                       "no llegaron a la prepa."},
            {"id": "p05", "narracion": "Otros planteles los respaldaron. Y ellos se disculparon."},
            {"id": "p06", "narracion": "El prejuicio lo firmó un decreto."},
            {"id": "p07", "narracion": "De eso nadie se ha disculpado. ¿Fue humor o fue discriminación?"},
            {"id": "p08", "narracion": "Aquí el dato mata al gato."},
        ],
    }


def test_la_formula_entera_pasa():
    assert instruccion_polemica.problemas(_base()) == []


def test_la_prueba_del_papel_manda_los_insultos_a_la_otra_formula():
    """El guion viral del Conalep (16/10/2026) acabó preguntando "¿dónde está el
    informe de empleabilidad?" a gente que llegó enojada porque ofendieron a su
    escuela. La fórmula del rumor asume que la disputa es sobre un hecho."""
    viral = instruccion_viral.instruccion(3, None, "-")
    assert "LA PRUEBA DEL PAPEL" in viral
    assert "instruccion_polemica" in viral
    # Y la señal de que te está pasando: el nivel 3 queda en una obviedad.
    assert "puede probarlo ni descartarlo" in viral

    polemica = instruccion_polemica.instruccion(3, "conalep bandidos del jale", "-")
    assert "¿EXISTE UN PAPEL QUE, SI APARECIERA, CERRARÍA LA DISCUSIÓN?" in polemica
    assert "por_que_esta_formula" in polemica

    sin_prueba = _base()
    del sin_prueba["_schema"]["por_que_esta_formula"]
    assert "por_que_esta_formula" in " ".join(instruccion_polemica.problemas(sin_prueba))


def test_la_instruccion_dice_los_tipos_validos_de_visual():
    """Claude escribió "archivo" en vez de "archivo_historico" y el video murió
    al generar, quemando los dos intentos (15/10/2026)."""
    texto = instruccion_polemica.instruccion(3, "conalep", "-")
    for tipo in revision_guion._VISUAL_TIPOS:
        assert tipo in texto, f"la instrucción no nombra {tipo}"
    assert "NO existe el tipo \"archivo\"" in texto


def test_sin_tema_la_instruccion_busca_polemicas():
    con = instruccion_polemica.instruccion(5, "conalep", "-")
    sin = instruccion_polemica.instruccion(5, None, "-")
    assert "QUÉ POLÉMICA HAY" in sin and "QUÉ POLÉMICA HAY" not in con
    assert "EL UMBRAL" in sin and "DOS de estas señales" in sin


def test_la_opinion_no_se_verifica_se_desempaca():
    """"Son bandidazos" no se refuta. Lo que se refuta es lo que la mala fama
    DICE en concreto, y eso no se infiere: se saca del rumor (Javier,
    17/10/2026: "el dato no debe de ser verídico... tiene que ser sobre los
    rumores")."""
    texto = instruccion_polemica.instruccion(1, "x", "-")
    assert "SE DESEMPACA" in texto
    assert "El dato no mata la opinión. Mata el prejuicio que la sostiene." in texto
    assert "EL PAPEL QUE DOCUMENTA EL RUMOR" in texto

    sin_premisas = _base()
    del sin_premisas["_schema"]["premisas"]
    assert "premisas" in " ".join(instruccion_polemica.problemas(sin_premisas))

    # Cada premisa necesita las DOS fuentes: la que prueba que se dice y la que
    # la contesta. El rumor también se prueba.
    sin_rumor = _base()
    del sin_rumor["_schema"]["premisas"][0]["fuente_del_rumor"]
    fallas = " ".join(instruccion_polemica.problemas(sin_rumor))
    assert "premisas[0]" in fallas and "fuente_del_rumor" in fallas

    inventada = _base()
    inventada["_schema"]["premisas"][0]["fuente_del_rumor"] = "me_lo_contaron"
    fallas = " ".join(instruccion_polemica.problemas(inventada))
    assert "no es una clave de _schema.fuentes" in fallas
    assert "El rumor también se prueba" in fallas

    # El dato contesta lo que el rumor DICE, no lo que convenga: la primera
    # versión del POC contestaba "no tiene futuro laboral" con las becas del
    # sector privado, una premisa que nadie estaba discutiendo.
    desviado = _base()
    desviado["_schema"]["premisas"][0]["dato"] = ("Cuarenta y dos mil becas las paga el sector "
                                                  "privado (encuesta_oficial)")
    fallas = " ".join(instruccion_polemica.problemas(desviado))
    assert "no habla de lo que dice" in fallas and "premisas[0].dice" in fallas

    # El candado no se cumple con la cita: una clave de fuente que lleve el
    # tema dentro ("anuario_conalep_2024") hacía pasar cualquier dato.
    por_la_cita = _base()
    por_la_cita["_schema"]["fuentes"]["dato_de_embarazadas"] = "https://www.inegi.org.mx/x.pdf"
    por_la_cita["_schema"]["premisas"][0]["dato"] = "Cuarenta y dos mil becas (dato_de_embarazadas)"
    por_la_cita["_schema"]["premisas"][0]["fuente_del_dato"] = "dato_de_embarazadas"
    assert "no habla de lo que dice" in " ".join(instruccion_polemica.problemas(por_la_cita))


def test_la_prueba_del_ofensor():
    """El guion viral eligió "9,360 colocados" de 79,363 egresados: el
    espectador hostil divide, le sale 12% y el video le da munición al insulto
    (16/10/2026)."""
    texto = instruccion_polemica.instruccion(1, "x", "-")
    assert "LA PRUEBA DEL OFENSOR" in texto
    assert "Si le sirve, NO es tu dato." in texto

    sin_prueba = _base()
    del sin_prueba["_schema"]["prueba_del_ofensor"]
    assert "prueba_del_ofensor" in " ".join(instruccion_polemica.problemas(sin_prueba))


def test_no_es_chisme_el_ofendido_es_un_colectivo():
    texto = instruccion_polemica.instruccion(1, "x", "-")
    assert "NO ES CHISME" in texto
    assert "es chisme de espectáculos y el tema NO va" in texto

    sin_candado = _base()
    del sin_candado["_schema"]["no_es_chisme"]
    assert "no_es_chisme" in " ".join(instruccion_polemica.problemas(sin_candado))


def test_la_frase_se_cita_en_los_primeros_planos():
    """Quien ve el video no vio la polémica. Si la frase no se dice, no se
    entiende de qué va: es lo que hundió el video de MINISO (16/10/2026)."""
    muda = _base()
    muda["planos"][0]["narracion"] = "Un podcast se burló de toda una escuela."
    muda["planos"][2]["narracion"] = "Ximena contestó: mi mamá se friega trabajando por el camión al plantel."
    fallas = " ".join(instruccion_polemica.problemas(muda))
    assert "no dice la frase" in fallas

    sin_frase = _base()
    del sin_frase["_schema"]["frase"]
    assert "_schema.frase" in " ".join(instruccion_polemica.problemas(sin_frase))


def test_la_respuesta_se_dice_no_se_cuenta():
    """En el guion viral del Conalep la cita de la alumna estaba en
    _schema.fuentes y la voz nunca la dijo, que era el video entero."""
    texto = instruccion_polemica.instruccion(1, "x", "-")
    assert "LA RESPUESTA SE DICE, NO SE CUENTA" in texto

    muda = _base()
    muda["planos"][2]["narracion"] = "Ximena le contestó con un video."
    muda["planos"][5]["narracion"] = "Otras escuelas los respaldaron. Y ellos se disculparon."
    fallas = " ".join(instruccion_polemica.problemas(muda))
    assert "reaccion.cita" in fallas

    # La reacción entra como hecho registrado, nunca como sentir.
    sin_cifra = _base()
    sin_cifra["_schema"]["reaccion"]["numeros"] = "la gente está indignada"
    fallas = " ".join(instruccion_polemica.problemas(sin_cifra))
    assert "no trae cifra" in fallas

    sin_reaccion = _base()
    del sin_reaccion["_schema"]["reaccion"]
    assert "_schema.reaccion" in " ".join(instruccion_polemica.problemas(sin_reaccion))


def test_la_disculpa_es_un_hecho_y_no_rompe_la_formula():
    """Lo destapó el POC: Los Parrilleros MX se disculparon el 17/10/2026, un día
    después, así que "quien lo dijo no ha contestado" dejó de ser cierto. Pedir
    "quién no ha contestado" obligaba a que alguien callara, o a inventarlo."""
    texto = instruccion_polemica.instruccion(1, "x", "-")
    assert "LA DISCULPA ES EL HECHO, NO EL FINAL" in texto

    # Sin nadie a quien le falte contestar, el guion sigue siendo válido: el
    # hueco es lo que la disculpa no toca.
    resuelta = _base()
    del resuelta["_schema"]["reaccion"]["no_contestaron"]
    assert instruccion_polemica.problemas(resuelta) == []

    # Lo que sí es obligatorio es decir QUÉ contestó quien dijo la frase.
    callada = _base()
    del callada["_schema"]["reaccion"]["respuesta_del_senalado"]
    fallas = " ".join(instruccion_polemica.problemas(callada))
    assert "respuesta_del_senalado" in fallas and "la disculpa es un hecho" in fallas

    # Y el hueco de la fórmula va escrito.
    sin_hueco = _base()
    del sin_hueco["_schema"]["lo_que_sigue_sin_contestar"]
    assert "lo_que_sigue_sin_contestar" in " ".join(instruccion_polemica.problemas(sin_hueco))


def test_el_veredicto_lo_pone_quien_ve():
    """17/10/2026, Javier: "tienes que pedir la opinión de los que ven esa
    polémica". Donde no hay fuente de la verdad, el veredicto es del público."""
    texto = instruccion_polemica.instruccion(1, "x", "-")
    assert "EL VEREDICTO ES DEL PÚBLICO" in texto

    sin = _base()
    del sin["_schema"]["veredicto"]
    assert "_schema.veredicto" in " ".join(instruccion_polemica.problemas(sin))

    # El canal no dictamina: pregunta.
    afirmado = _base()
    afirmado["_schema"]["veredicto"]["pregunta"] = "Fue discriminación, claramente."
    assert "no es una pregunta" in " ".join(instruccion_polemica.problemas(afirmado))

    # Un solo lado es el canal opinando con signo de interrogación.
    un_lado = _base()
    un_lado["_schema"]["veredicto"]["lados"] = ["discriminación"]
    assert "veredicto.lados" in " ".join(instruccion_polemica.problemas(un_lado))

    # Y la pregunta se DICE en el cierre, no se queda en el _schema.
    muda = _base()
    muda["planos"][7]["narracion"] = "De eso nadie se ha disculpado. ¿Tú qué opinas?"
    fallas = " ".join(instruccion_polemica.problemas(muda))
    assert "no pide el veredicto" in fallas


def test_dos_piezas_de_redes_la_causa_y_la_respuesta():
    """El guion viral del Conalep traía una sola captura de perfil: no se veía
    ni lo que se dijo ni quién contestó."""
    una = _base()
    una["evidencia"] = [{"tipo": "red_social"}, {"tipo": "documento"}, {"tipo": "prensa"}]
    fallas = " ".join(instruccion_polemica.problemas(una))
    assert "pieza(s) de redes" in fallas and "la CAUSA" in fallas

    # El documento es deseable, no obligatorio: aquí la fuente primaria puede
    # quedar en una ficha. Es al revés que en la fórmula del rumor.
    sin_doc = _base()
    sin_doc["evidencia"] = [{"tipo": "red_social"}, {"tipo": "video_red"}, {"tipo": "prensa"}]
    assert instruccion_polemica.problemas(sin_doc) == []


def test_el_insulto_no_se_anima_en_la_nota():
    sin_veto = _base()
    sin_veto["plus"]["sin_nota_animada"] = ["p00"]
    fallas = " ".join(instruccion_polemica.problemas(sin_veto))
    assert "sin_nota_animada" in fallas and "p01" in fallas


def test_el_nombre_se_dice_no_se_ensena():
    mudo = _base()
    mudo["_schema"]["senalados"] = ["Conalep", "Ximena", "Los Parrilleros MX"]
    fallas = " ".join(instruccion_polemica.problemas(mudo))
    assert "Los Parrilleros MX" in fallas and "captura no basta" in fallas


def test_el_check_final_pide_cada_dato_con_su_fuente():
    flojo = _base()
    flojo["_schema"]["verificacion_final"]["datos"] = ["una sola cosa"]
    assert "verificacion_final.datos" in " ".join(instruccion_polemica.problemas(flojo))

    suelto = _base()
    suelto["_schema"]["verificacion_final"]["datos"][1] = "cuarenta y dos mil becas"
    assert "no nombran su clave" in " ".join(instruccion_polemica.problemas(suelto))


def test_la_polemica_se_descubre_en_la_plataforma():
    portal = _base()
    portal["_schema"]["hallado_en"] = "Lo publicó La Crónica el 16 de octubre de 2026"
    assert "no nombra una plataforma" in " ".join(instruccion_polemica.problemas(portal))

    sin_cifra = _base()
    sin_cifra["_schema"]["hallado_en"] = "TikTok, en la cuenta de una alumna"
    assert "no trae los números" in " ".join(instruccion_polemica.problemas(sin_cifra))


def test_revisar_corre_las_reglas_de_polemica(tmp_path, monkeypatch):
    """`revisar` es lo que Claude corre MIENTRAS escribe: tiene que reconocer la
    fórmula por el _schema y aplicarle sus reglas, no las del rumor."""
    from dato_mata_gato_bot import fabrica, herramientas_guion

    monkeypatch.setattr(fabrica.pipeline, "ANDROID_IN", tmp_path)
    monkeypatch.setattr(herramientas_guion, "problemas_de_evidencia", lambda g: [])
    guion = _base()
    guion["_schema"]["senalados"] = ["Conalep", "Ximena", "Los Parrilleros MX"]
    (tmp_path / "guion-polemica-x").mkdir()
    (tmp_path / "guion-polemica-x" / "guion.json").write_text(
        json.dumps(guion, ensure_ascii=False), encoding="utf-8")

    salida = herramientas_guion.revisar("guion-polemica-x")
    assert "Los Parrilleros MX" in salida, "revisar no corrió las reglas de la polémica"


def test_el_poc_del_conalep_pasa_la_formula():
    """El POC del 17/10/2026: el mismo tema que el guion viral, reescrito con
    esta fórmula. Si la carpeta de trabajo no está, no hay nada que probar."""
    from dato_mata_gato_bot import pipeline

    ruta = pipeline.ANDROID_IN / "guion-polemica-conalep-bandidos-del-jale" / "guion.json"
    if not ruta.exists():
        pytest.skip("el POC no está en esta máquina")
    guion = json.loads(ruta.read_text(encoding="utf-8"))
    # El POC es anterior al "_schema.que_paso" (27/10/2026): solo eso le puede faltar.
    assert [p for p in instruccion_polemica.problemas(guion) if "que_paso" not in p] == []
    # Lo que el POC tiene que demostrar: que el hueco sobrevive a la disculpa,
    # y que los datos son sobre lo que el rumor dice, no sobre otra cosa.
    assert guion["_schema"]["reaccion"]["respuesta_del_senalado"]
    assert "carrera técnica" in guion["_schema"]["lo_que_sigue_sin_contestar"]
    dice = " ".join(p["dice"] for p in guion["_schema"]["premisas"])
    assert "embarazadas" in dice and "asaltan" in dice


def test_la_frase_recortada_no_pasa_y_que_paso_se_dice():
    """27/10/2026, madres buscadoras: "vale más mi gato" sin "que sus desaparecidos"."""
    guion = {"planos": [
        {"id": "p00", "narracion": "Yuli Salgado les escribió: vale más mi gato."},
        {"id": "p01", "narracion": "Te imaginas a quien busca a su hijo. Una creadora dijo que su gato valía más."},
        {"id": "p02", "narracion": "El colectivo enseñó las capturas."}]}
    frase = {"texto": "vale más mi gato que sus desaparecidos", "quien": "Yuli Salgado", "donde": "TikTok"}
    fallas = instruccion_polemica._problemas_de_la_frase(guion, {"frase": frase})
    assert fallas  # recortada: "no dice la frase" o "dila COMPLETA", según cuánto falte
    que_paso = {"que_paso": "Una creadora de contenido le escribió a un colectivo de madres buscadoras "
                            "que su gato vale más que sus desaparecidos."}
    assert instruccion_polemica.problemas_de_que_paso(guion, que_paso, ("p00", "p01", "p02"))
    guion["planos"][1]["narracion"] = ("Una creadora de contenido le escribió en TikTok a un colectivo de "
                                       "madres buscadoras: vale más mi gato que sus desaparecidos.")
    assert instruccion_polemica._problemas_de_la_frase(guion, {"frase": frase}) == []
    assert instruccion_polemica.problemas_de_que_paso(guion, que_paso, ("p00", "p01", "p02")) == []
