"""La apertura del p01 se rota (Javier, 03/11/2026).

Hasta el 03/11 el 75% de los guiones abría con "Te imaginas a quien…": se nota
desde el perfil y cae en el segundo en que TikTok decide si reparte. Las cuatro
fórmulas del canal comparten `instruccion_cercania.APERTURAS_P01`.
"""

import re

from dato_mata_gato_bot import (
    instruccion_cercania,
    instruccion_comparativa,
    instruccion_polemica,
    instruccion_viral,
)


def instrucciones() -> dict[str, str]:
    """El prompt que de verdad se le manda a Claude, por fórmula."""
    return {
        "cercania": instruccion_cercania.instruccion(
            "cancun", 2, "nada", vigencia="conversacion"
        ),
        "viral": instruccion_viral.instruccion(2, None, "nada"),
        "polemica": instruccion_polemica.instruccion(2, None, "nada"),
        "comparativa": instruccion_comparativa.instruccion(2, None, "nada"),
    }


def test_no_quedan_placeholders_sin_sustituir():
    """Un <<LO_QUE_SEA>> suelto se le iría a Claude tal cual."""
    for nombre, texto in instrucciones().items():
        sueltos = set(re.findall(r"<<[A-Z_]+>>", texto))
        assert not sueltos, f"{nombre} dejó sin sustituir: {sueltos}"


def test_las_tres_formulas_rotan_la_apertura():
    """Cercanía, viral y polémica traen las seis aperturas."""
    for nombre in ("cercania", "viral", "polemica"):
        texto = instrucciones()[nombre]
        assert "ROTA LA APERTURA" in texto, f"{nombre} sin la rotación"
        faltan = [x for x in "abcdef" if f"    {x}) " not in texto]
        assert not faltan, f"{nombre} le faltan opciones: {faltan}"


def test_te_imaginas_ya_no_es_la_unica():
    """Sigue disponible como opción (a), pero ya no es la instrucción fija."""
    for nombre in ("cercania", "viral", "polemica"):
        texto = instrucciones()[nombre]
        assert "Te imaginas a quien" in texto
        assert "úsala solo si" in texto, f"{nombre} no la degrada a una de seis"


def test_la_comparativa_sigue_sin_apertura_de_te_imaginas():
    """Javier ya la había sacado de la comparativa; eso no cambió."""
    texto = instrucciones()["comparativa"]
    assert "aquí NO va" in texto


def test_el_caso_local_que_destapa_un_numero_nacional():
    """La forma que más se comparte (03/11/2026) va en LO QUE SUMA."""
    texto = instrucciones()["cercania"]
    assert "NÚMERO NACIONAL" in texto


def test_los_ejemplos_de_pregunta_son_de_si_o_no():
    """La regla del 21/10: ninguna pregunta de ejemplo abre con qué/cómo/cuál."""
    malas = []
    for nombre, texto in instrucciones().items():
        for pregunta in re.findall(r"¿([^?]{3,60})\?", texto):
            arranque = pregunta.strip().lower()
            if arranque.startswith(("qué ", "que ", "cómo ", "como ", "cuál ", "cual ",
                                    "cuánto ", "cuanto ", "por qué ")):
                # Solo las que le hablan a quien ve (de tú).
                if re.search(r"\b(tú|ti|te|tu|tus)\b", arranque):
                    malas.append((nombre, pregunta))
    assert not malas, f"ejemplos que no son de sí o no: {malas}"
