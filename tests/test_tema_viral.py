"""Fórmula del tema viral y el bug de /pararfabrica (15/10/2026)."""

import json

from dato_mata_gato_bot import fabrica, instruccion_viral, revision_guion


def _base() -> dict:
    """Un guion viral que pasa todas las revisiones de la fórmula."""
    return {
        "_schema": {
            "que_paso": "Dos millones vieron al gerente de MINISO en esa tienda.",
            "tres_niveles": {"se_dice": "x", "esta_documentado": "x",
                             "no_se_sabe": "x", "pendiente_de_pedir": "x"},
            "vale_sin_el_rumor": "x",
            "pregunta_del_publico": "¿Y a la tienda qué le pasa cuando te discriminan ahí?",
            "preguntas_abiertas": ["¿Se perdió?", "¿O no quieren que lo veas?"],
            "condiciones": {c: "x" for c in instruccion_viral.CONDICIONES},
            "senalados": ["MINISO", "COPRED"],
            "hallado_en": "TikTok, @max_cintio, 2.5 millones de vistas, 06/10/2026",
            "fuentes": {"infobae_miniso": "https://www.infobae.com/mexico/2026/10/07/x/",
                        "copred_edis": "https://copred.cdmx.gob.mx/nota/x"},
            "verificacion_final": {
                "datos": ["dos millones y medio de vistas -- infobae_miniso",
                          "cuarenta y seis por ciento -- copred_edis",
                          "trece de octubre de dos mil veintiséis -- copred_edis"],
                "misma_historia": "Arranca en la tienda y p03 a p07 contestan qué le pasa.",
                "corregido": "nada"},
        },
        "evidencia": [{"tipo": "documento"}, {"tipo": "video_red"}],
        "plus": {"sin_nota_animada": ["p00", "p01", "p02"]},
        "planos": [
            {"id": "p00", "narracion": "Dos millones y medio vieron al gerente de MINISO."},
            {"id": "p01", "narracion": "Te imaginas a quien entra a esa tienda. ¿Tú lo viste?"},
            {"id": "p02", "narracion": "No se lo inventaron: ya había pasado antes."},
            {"id": "p03", "narracion": "¿Y a la tienda qué le pasa? La ley sí permite multarla."},
            {"id": "p04", "narracion": "El COPRED midió que muchos ya fueron discriminados."},
            {"id": "p05", "narracion": "La empresa dijo que lo desvinculó."},
            {"id": "p06", "narracion": "La reforma se publicó en dos mil veintitrés."},
            {"id": "p07", "narracion": "Nadie ha publicado cuántas tiendas fueron multadas."},
            {"id": "p08", "narracion": "Aquí el dato mata al gato."},
        ],
    }


def test_la_instruccion_dice_los_tipos_validos_de_visual():
    """Claude escribió "archivo" en vez de "archivo_historico" y el video murió
    al generar, quemando los dos intentos: la instrucción no los listaba."""
    texto = instruccion_viral.instruccion(3, "israel y yucatan", "-")
    for tipo in revision_guion._VISUAL_TIPOS:
        assert tipo in texto, f"la instrucción no nombra {tipo}"
    assert "NO existe el tipo \"archivo\"" in texto


def test_visual_tipo_invalido_se_atrapa_antes_de_generar():
    guion = {"planos": [
        {"id": "p00", "visual": {"tipo": "archivo"}},
        {"id": "p01", "visual": {"tipo": "archivo_historico"}},
        {"id": "p08", "visual": {"tipo": "grafico_movimiento"}}]}
    fallas = " ".join(revision_guion.problemas(guion, min_nombres=0))
    assert "visual.tipo inválido" in fallas and "p00" in fallas
    assert "p01" not in fallas.split("visual.tipo inválido")[1].split(".")[0]


def test_sin_tema_la_instruccion_busca_tendencias():
    con = instruccion_viral.instruccion(5, "israel y yucatan", "-")
    sin = instruccion_viral.instruccion(5, None, "-")
    assert "DE QUÉ SE ESTÁ HABLANDO" in sin and "DE QUÉ SE ESTÁ HABLANDO" not in con
    # No vale un tema viral sin dato propio debajo: ahí el canal solo repetiría.
    assert "NO lo tomes aunque esté muy viral" in sin


def test_las_nueve_piezas_y_el_candado():
    base = _base()
    assert instruccion_viral.problemas(base) == []

    sin_candado = json.loads(json.dumps(base))
    del sin_candado["_schema"]["vale_sin_el_rumor"]
    assert "vale_sin_el_rumor" in " ".join(instruccion_viral.problemas(sin_candado))

    sin_fama = json.loads(json.dumps(base))
    del sin_fama["_schema"]["condiciones"]["8_por_que_se_cree"]
    assert "8_por_que_se_cree" in " ".join(instruccion_viral.problemas(sin_fama))

    sin_doc = json.loads(json.dumps(base))
    sin_doc["evidencia"] = [{"tipo": "prensa"}, {"tipo": "video_red"}]
    assert "documento" in " ".join(instruccion_viral.problemas(sin_doc))

    # El tema nació en redes: hay que enseñarlo, no contarlo de oídas.
    sin_redes = json.loads(json.dumps(base))
    sin_redes["evidencia"] = [{"tipo": "documento"}, {"tipo": "prensa"}]
    assert "redes" in " ".join(instruccion_viral.problemas(sin_redes))

    # El desvío del 15/10: sin la pregunta, el nivel 2 se va por otro lado.
    sin_pregunta = json.loads(json.dumps(base))
    del sin_pregunta["_schema"]["pregunta_del_publico"]
    assert "pregunta_del_publico" in " ".join(instruccion_viral.problemas(sin_pregunta))

    # Animar el cuerpo del artículo que afirma el rumor es publicarlo.
    sin_veto = json.loads(json.dumps(base))
    sin_veto["plus"]["sin_nota_animada"] = ["p00"]
    fallas = " ".join(instruccion_viral.problemas(sin_veto))
    assert "sin_nota_animada" in fallas and "p01" in fallas


def test_pararfabrica_no_se_pierde_mientras_claude_escribe(tmp_path, monkeypatch):
    """El ciclo lee el estado al empezar y lo guarda horas después; si entre
    medias entró un /pararfabrica, la copia vieja revivía el lote y la tarea de
    Windows lo retomaba. Pasó con viral-20261015-1856: Javier canceló un lote de
    5 y se generó igual."""
    monkeypatch.setattr(fabrica, "RAIZ", tmp_path)
    (tmp_path / "L").mkdir()
    fabrica.guardar("L", {"lote": "L", "terminado": False, "videos": {}})

    viejo = fabrica.leer("L")          # lo que el ciclo trae en memoria
    assert not fabrica.detenida("L")

    estado = fabrica.leer("L")         # /pararfabrica, en el bot
    estado["terminado"], estado["detenida"] = True, "2026-10-15T19:00"
    fabrica.guardar("L", estado)
    assert fabrica.detenida("L")

    viejo["videos"]["x"] = {"estado": "listo"}   # el ciclo guarda lo suyo
    fabrica.guardar("L", viejo)

    final = fabrica.leer("L")
    assert final["terminado"] is True, "el ciclo revivió un lote cancelado"
    assert final["detenida"] == "2026-10-15T19:00"
    assert final["videos"] == {"estado": "listo"} or "x" in final["videos"]


def test_evidencia_de_redes_cuenta_como_real():
    """Una publicación de redes es evidencia del fenómeno, no relleno: sin ella
    el video cuenta un viral sin enseñarlo (Javier, 15/10/2026)."""
    from dato_mata_gato_bot import evidencia, evidencia_redes

    assert evidencia.DE_REDES <= evidencia.REALES
    assert evidencia_redes.es_red_social("https://www.tiktok.com/@x/video/1")
    assert evidencia_redes.es_red_social("https://fb.watch/abc/")
    assert not evidencia_redes.es_red_social("https://www.poresto.com/nota.html")
    assert evidencia_redes.red_de("https://vt.tiktok.com/ZSg/") == "TikTok"
    # El crédito es del autor de la publicación, no del sitio.
    assert evidencia_redes._credito({"url": "https://www.tiktok.com/@a/video/1"},
                                    {"uploader": "@vicky_wolff"}) == "@vicky_wolff · TikTok"


def test_el_candado_pide_que_sea_sobre_lo_mismo():
    """El guion del 15/10 arrancó con el video de un hombre fingiendo
    discapacidad y se fue a multas de estacionamiento: cumplía "vale solo" pero
    no "es sobre lo mismo"."""
    texto = instruccion_viral.instruccion(1, "x", "-")
    assert "SOBRE LO MISMO QUE EL RUMOR" in texto
    assert "pregunta_del_publico" in texto


def test_el_umbral_mide_el_fenomeno_no_que_exista_la_nota():
    sin = instruccion_viral.instruccion(3, None, "-")
    assert "EL UMBRAL" in sin and "DOS de estas señales" in sin
    assert "tres portales locales NO es un fenómeno" in sin


def test_el_nivel_3_cierra_abriendo():
    """Pieza 9 (Javier, 15/10/2026): "eso hay que cuestionarlo, lanzar preguntas
    que la gente responde y opine, y dar suposiciones". Van en pregunta, nunca
    afirmadas: el canal no tiene documento para afirmar una intención."""
    base = _base()
    assert instruccion_viral.problemas(base) == []

    una_sola = json.loads(json.dumps(base))
    una_sola["_schema"]["preguntas_abiertas"] = ["¿Se perdió?"]
    assert "preguntas_abiertas" in " ".join(instruccion_viral.problemas(una_sola))

    # Afirmar una intención sin documento es lo único que puede costar la cuenta.
    afirmada = json.loads(json.dumps(base))
    afirmada["_schema"]["preguntas_abiertas"] = ["Lo esconden porque hay corrupción", "¿Se perdió?"]
    fallas = " ".join(instruccion_viral.problemas(afirmada))
    assert "en pregunta, no en afirmación" in fallas

    texto = instruccion_viral.instruccion(1, "x", "-")
    assert "LA PREGUNTA QUE QUEDA" in texto
    assert "explicación inocente" in texto


def test_el_nombre_se_dice_no_se_ensena():
    """El video de MINISO (2.5 M de vistas, 16/10/2026): el nombre salía en la
    captura del titular de Infobae y la voz nunca lo pronunció. Javier: "el
    título dice de un caso de Miniso, pero realmente no se da un contexto claro
    de quién y qué pasó"."""
    mudo = _base()
    mudo["planos"][0]["narracion"] = "Dos millones y medio vieron el video. La tienda lo despidió."
    fallas = " ".join(instruccion_viral.problemas(mudo))
    assert "MINISO" in fallas and "captura no basta" in fallas

    sin_lista = _base()
    del sin_lista["_schema"]["senalados"]
    assert "senalados" in " ".join(instruccion_viral.problemas(sin_lista))


def test_menores_es_la_unica_excepcion_para_nombrar():
    """16/10/2026, Javier: fuera de los menores de edad, "que sea claro y diga
    nombres de manera transparente". Un señalado sin sentencia se nombra; lo
    que cambia es el verbo, no el nombre."""
    texto = instruccion_viral.instruccion(1, "x", "-")
    assert "UNA sola excepción" in texto and "MENORES DE EDAD" in texto
    assert "Una persona señalada y sin sentencia SÍ se nombra" in texto
    assert "NO hay nombre que se calle" in texto
    # Y el nivel 1 se cuenta: quien ve el video no vio el viral.
    assert "EL NIVEL 1 SE CUENTA, NO SE DA POR SABIDO" in texto


def test_el_check_final_pide_cada_dato_con_su_fuente():
    """16/10/2026, Javier: "verifica si la información es correcta"."""
    assert "EL CHECK FINAL" in instruccion_viral.instruccion(1, "x", "-")

    flojo = _base()
    flojo["_schema"]["verificacion_final"]["datos"] = ["una sola cosa"]
    assert "verificacion_final.datos" in " ".join(instruccion_viral.problemas(flojo))

    # Un renglón que no dice de qué fuente sale no es una verificación.
    suelto = _base()
    suelto["_schema"]["verificacion_final"]["datos"][1] = "cuarenta y seis por ciento"
    fallas = " ".join(instruccion_viral.problemas(suelto))
    assert "no nombran su clave de _schema.fuentes" in fallas

    sin_historia = _base()
    sin_historia["_schema"]["verificacion_final"]["misma_historia"] = ""
    assert "misma_historia" in " ".join(instruccion_viral.problemas(sin_historia))


def test_el_check_final_atrapa_el_desvio():
    """"Me dio una ligera impresión de que desviabas el tema" (Javier,
    16/10/2026). El nivel 2 tiene que contestar la pregunta del público, no una
    parecida: el 15/10 el guion arrancó con un hombre fingiendo discapacidad y
    terminó en multas de estacionamiento."""
    desviado = _base()
    for plano in desviado["planos"]:
        if plano["id"] in instruccion_viral.PLANOS_DEL_DATO:
            plano["narracion"] = "El reglamento de estacionamientos cobra multas desde dos mil."
    fallas = " ".join(instruccion_viral.problemas(desviado))
    assert "no hablan de nada de lo que pregunta" in fallas

    # Y no al revés: contestar la MISMA pregunta con otras palabras sí pasa.
    # Pedir dos coincidencias marcaba guion-viral-pasaporte-sitio-falso, que
    # pregunta "¿cómo le pagué por una cita si la cita no se paga?" y contesta
    # "agendarla no cuesta nada y sólo se paga en bancos" (16/10/2026).
    pasaporte = _base()
    pasaporte["_schema"]["pregunta_del_publico"] = ("¿Cómo le pagué por una cita de pasaporte "
                                                    "si la cita no se paga?")
    for plano in pasaporte["planos"]:
        if plano["id"] == "p03":
            plano["narracion"] = "¿La cita se paga? No: agendarla no cuesta nada."
        elif plano["id"] == "p06":
            plano["narracion"] = "El pasaporte de tres años cuesta mil setecientos pesos."
    assert instruccion_viral.problemas(pasaporte) == []


def test_el_aviso_trae_titulo_y_hashtags(tmp_path, monkeypatch):
    """16/10/2026, Javier: "que devuelva con el video el nombre del título y
    los hashtags para la viralidad". Antes había que abrir el guion.json a mano
    para saber con qué publicarlo."""
    monkeypatch.setattr(fabrica.pipeline, "ANDROID_IN", tmp_path)
    (tmp_path / "g").mkdir()
    (tmp_path / "g" / "guion.json").write_text(json.dumps({
        "titulo": "La clínica de la liposucción", "gancho": "17 FALTAS SANITARIAS",
        "hashtags": ["#DatoMataGato", "CDMX"]}, ensure_ascii=False), encoding="utf-8")

    salida = fabrica.para_publicar("g")
    assert "La clínica de la liposucción" in salida
    # El gancho es el texto de la portada, no va en el bloque de publicar.
    assert "17 FALTAS SANITARIAS" not in salida
    # El hashtag que viene sin almohadilla la recibe: se copia y se pega tal cual.
    assert "#DatoMataGato #CDMX" in salida

    assert fabrica.para_publicar("no-existe") == ""


def test_el_tema_se_busca_en_la_plataforma_no_en_los_portales():
    """16/10/2026, Javier: "esos temas virales los tienes que buscar en redes
    sociales... el tema de Vicky Wolff salió porque era un tema popular en la
    plataforma". Un tema encontrado en un portal es una noticia, y para eso
    está la fórmula de cercanía."""
    sin = _base()
    del sin["_schema"]["hallado_en"]
    assert "hallado_en" in " ".join(instruccion_viral.problemas(sin))

    # Sin plataforma nombrada no se sabe dónde se descubrió.
    portal = _base()
    portal["_schema"]["hallado_en"] = "Lo publicó Infobae el 13 de octubre de 2026"
    assert "no nombra una plataforma" in " ".join(instruccion_viral.problemas(portal))

    # Sin números no se sabe si de verdad está dando conversación.
    sin_cifra = _base()
    sin_cifra["_schema"]["hallado_en"] = "TikTok, en la cuenta de un creador"
    assert "no trae los números" in " ".join(instruccion_viral.problemas(sin_cifra))

    texto = instruccion_viral.instruccion(3, None, "-")
    assert "EL TEMA SALE DE LA PLATAFORMA, NO DE LA PRENSA" in texto
    assert "hallado_en" in texto
    # La prensa confirma, no descubre.
    assert "Nunca para descubrir el tema" in texto


def test_cambiar_la_fuente_de_una_pieza_la_recaptura():
    """El caché iba por `id` a secas: corregirle la URL a una pieza ya armada
    no servía, se quedaba el JPG viejo. Así fue como el video de MINISO salió
    enseñando la nota de la EDIS 2017 ("Publicado el 31 Agosto 2017") rotulada
    "COPRED, EDIS 2026" (16/10/2026)."""
    from dato_mata_gato_bot import evidencia

    pieza = {"id": "e2", "tipo": "documento", "url": "https://copred.cdmx.gob.mx/nota/edis-2017"}
    guardada = {"tipo": "documento", "fuente": pieza["url"], "huella": evidencia._huella(pieza)}
    assert not evidencia._cambio(pieza, guardada)

    corregida = {**pieza, "url": "https://copred.cdmx.gob.mx/nota/establecimientos"}
    assert evidencia._cambio(corregida, guardada), "la URL cambió y no se recaptura"

    # Una ficha con otros renglones también es otra pieza.
    ficha = {"id": "f1", "tipo": "ficha", "titulo": "T", "renglones": ["4 410 entrevistas"]}
    vieja = {"tipo": "ficha", "huella": evidencia._huella(ficha)}
    assert evidencia._cambio({**ficha, "renglones": ["5 200 entrevistas"]}, vieja)

    # Manifest viejo (sin huella): al menos la URL se compara.
    sin_huella = {"tipo": "documento", "fuente": pieza["url"]}
    assert evidencia._cambio(corregida, sin_huella)
    assert not evidencia._cambio(pieza, sin_huella)


def test_revisar_corre_las_reglas_virales(tmp_path, monkeypatch):
    """`revisar` es lo que Claude corre MIENTRAS escribe, y solo revisaba las
    reglas de cercanía: las virales salían después de entregar el lote, en la
    ronda de corrección (16/10/2026)."""
    from dato_mata_gato_bot import herramientas_guion

    monkeypatch.setattr(fabrica.pipeline, "ANDROID_IN", tmp_path)
    monkeypatch.setattr(herramientas_guion, "problemas_de_evidencia", lambda g: [])
    guion = _base()
    guion["planos"][0]["narracion"] = "Dos millones y medio vieron el video. La tienda lo despidió."
    (tmp_path / "guion-viral-x").mkdir()
    (tmp_path / "guion-viral-x" / "guion.json").write_text(
        json.dumps(guion, ensure_ascii=False), encoding="utf-8")

    salida = herramientas_guion.revisar("guion-viral-x")
    assert "MINISO" in salida, "revisar no corrió las reglas de la fórmula viral"


def test_el_prompt_largo_no_revienta_la_linea_de_comandos(monkeypatch):
    """El lote viral del 16/10/2026 murió 17 ciclos seguidos sin escribir un
    guion: el prompt iba como argumento y Windows corta en 32 767 caracteres
    (CreateProcess -> WinError 206). Reventaba ANTES de arrancar Claude, así
    que no dejaba ni sesión ni error. Ahora va por stdin."""
    from dato_mata_gato_bot import claude_runner

    visto = {}

    def falso_run(args, **kw):
        visto["args"] = args
        visto["input"] = kw.get("input")

        class R:
            returncode = 0
            stdout = '{"result": "listo"}'
            stderr = ""
        return R()

    monkeypatch.setattr(claude_runner.subprocess, "run", falso_run)
    enorme = "x" * 40000
    r = claude_runner.run_turn("sess", enorme, True)

    assert r.ok
    assert visto["input"] == enorme, "el prompt tiene que viajar por stdin"
    assert enorme not in " ".join(visto["args"]), "el prompt no puede ir en la linea de comandos"
    assert len(" ".join(visto["args"])) < 32767


def test_un_error_dentro_del_json_no_pasa_por_turno_bueno():
    """Claude puede salir con codigo 0 y el error dentro del JSON."""
    from dato_mata_gato_bot import claude_runner

    r = claude_runner._parse_output('{"is_error": true, "result": "API overloaded"}')
    assert not r.ok and "API overloaded" in r.text
    assert claude_runner._parse_output('{"is_error": false, "result": "ok"}').ok
