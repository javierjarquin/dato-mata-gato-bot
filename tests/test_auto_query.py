from dato_mata_gato_bot import auto_query


def test_extract_keywords_toma_nombres_propios_en_orden_sin_repetidos():
    narracion = (
        "Alan Turing trabajó en Bletchley Park. Turing rompió el código de la "
        "máquina Enigma junto a otros criptógrafos."
    )
    assert auto_query.extract_keywords(narracion) == ["Alan Turing", "Bletchley Park"]


def test_extract_keywords_descarta_mayuscula_de_inicio_de_oracion():
    # "Cuando algo" se agarra como una sola frase (mayúsculas contiguas) y se
    # descarta completa por empezar con una stopword.
    narracion = "El código se rompió en 1941. Cuando todo cambió, nadie lo notó."
    keywords = auto_query.extract_keywords(narracion)
    assert "El" not in keywords
    assert not any(k.startswith("Cuando") for k in keywords)
    assert keywords == []


def test_extract_keywords_respeta_max_terminos():
    narracion = "Ana Pérez conoció a Juan López en Ciudad de México, dice Marta Ruiz."
    assert len(auto_query.extract_keywords(narracion, max_terminos=1)) == 1


def test_extract_keywords_narracion_vacia():
    assert auto_query.extract_keywords("") == []
    assert auto_query.extract_keywords(None) == []


def test_build_query_combina_titulo_y_terminos():
    query = auto_query.build_query("Criptografía", "Alan Turing rompió Enigma.")
    assert query == "Criptografía Alan Turing Enigma"


def test_build_query_sin_titulo():
    query = auto_query.build_query("", "Alan Turing rompió Enigma.")
    assert query == "Alan Turing Enigma"


def test_build_query_sin_nombres_propios_devuelve_solo_titulo():
    query = auto_query.build_query("Criptografía", "el código se rompió ese día.")
    assert query == "Criptografía"
