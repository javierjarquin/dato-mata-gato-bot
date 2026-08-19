from dato_mata_gato_bot import image_naming


def test_parse_formato_basico():
    spec = image_naming.parse("p1 [inicio] [1]")
    assert spec.plano_id == "p01"
    assert spec.posicion == "inicio"
    assert spec.indice == 1


def test_parse_normaliza_a_dos_digitos():
    spec = image_naming.parse("p12 [fin] [3]")
    assert spec.plano_id == "p12"


def test_parse_es_insensible_a_mayusculas_y_espacios():
    spec = image_naming.parse("P1[MEDIO][2]")
    assert spec.posicion == "medio"
    assert spec.indice == 2


def test_parse_texto_no_reconocido_da_none():
    assert image_naming.parse("esto no sigue el formato") is None
    assert image_naming.parse("") is None
    assert image_naming.parse(None) is None


def test_filename_for():
    spec = image_naming.parse("p1 [inicio] [1]")
    assert image_naming.filename_for(spec, ".jpg") == "p01_inicio_1.jpg"
