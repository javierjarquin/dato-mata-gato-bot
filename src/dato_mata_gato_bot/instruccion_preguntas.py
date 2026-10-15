"""Instrucción para que Claude cargue preguntas nuevas al banco de trivias.

Se usa DENTRO de /lote, no como comando aparte: cuando el banco no alcanza
para las trivias del lote, se le piden las que faltan y se sigue. El usuario
revisa el lote entero al final, como siempre -- el resumen de cada trivia son
sus preguntas con la respuesta, así que la verificación pasa por ahí.

Su formato de salida está atado al parser de `_cargar_preguntas_al_banco`: si
se toca una, se toca la otra.
"""

INSTRUCCION_PREGUNTAS = (
    "Necesito preguntas nuevas para el banco de trivias del canal. Proponé {temas} tema(s) "
    "NUEVO(S), con {por_tema} preguntas cada uno. NO escribas ningún guion ni crees "
    "archivos: solo la lista.\n\n"
    "LÍNEA EDITORIAL: el canal es de true crime, así que la trivia va por el mismo lado. "
    "Datos reales que incomodan, sorprenden o dan un poco de escalofrío -- nada de cultura "
    "general blanda. El criterio para saber si una pregunta sirve: que el dato dé ganas de "
    "contárselo a alguien. Temas que funcionan: forense, venenos, animales letales, "
    "desapariciones, criminología, fugas y cárceles, estafas, desastres, el cuerpo al "
    "límite, océano profundo.\n\n"
    "TEMAS QUE YA ESTÁN EN EL BANCO (no los repitas): {ya_estan}\n\n"
    "REGLAS DURAS:\n"
    "1. El dato tiene que ser VERIFICABLE y de consenso. Si no estás seguro, no la "
    "propongas. Es la regla más importante de todas: el canal se llama Dato Mata Gato, y un "
    "dato falso en pantalla le cuesta más que diez videos flojos.\n"
    "2. Nada de casos con personas vivas identificables, ni detalles de métodos de "
    "suicidio, ni descripción de material filtrado de víctimas.\n"
    "3. La respuesta tiene que ser CORTA y decible en voz alta: un nombre, un número, una "
    "palabra. Si necesita una frase entera, la pregunta está mal planteada.\n"
    "4. `verificacion` explica POR QUÉ el dato es correcto y de dónde sale. Se guarda junto "
    "a la pregunta para poder re-chequearla después sin volver a investigar el tema.\n"
    "5. `busqueda_pregunta` y `busqueda_respuesta` van en INGLÉS y describen una escena "
    "concreta y fotografiable: se buscan en bancos de imágenes reales, así que nada "
    "abstracto ni de marca. OJO: la foto de la PREGUNTA no puede revelar la respuesta.\n"
    "6. De las {por_tema} preguntas de cada tema, un tercio 'facil', un tercio 'media' y un "
    "tercio 'dificil'. La rampa de dificultad es lo que sostiene la permanencia del video.\n"
    "7. LARGO, y esto es un presupuesto duro, no una sugerencia: `pregunta` como MUCHO 14 "
    "palabras, `respuesta` como mucho 5, `dato_extra` como mucho 12. Medido el 14/09/2026 "
    "sobre un lote real: con preguntas de 19 palabras y respuestas de 24, el video salió de "
    "124 segundos, más largo que los de crimen. Las seis preguntas con su respuesta tienen "
    "que entrar en unas 115 palabras entre todas. Si una pregunta no se puede hacer corta, "
    "cambiala por otra: 'qué patrón del cuerpo se usa desde hace más de un siglo para "
    "identificar personas de forma única' es la misma pregunta que 'qué identifica a una "
    "persona desde hace un siglo', y la segunda entra.\n"
    "8. Dentro de un mismo tema, que NO haya dos preguntas sobre el mismo hecho. En ese "
    "lote real salieron 'qué insectos llegan primero a un cuerpo' y 'cómo se llama la "
    "ciencia que estudia insectos para calcular la muerte': la segunda queda medio "
    "respondida por la primera, y el video se desinfla.\n\n"
    "Respondé ÚNICAMENTE con este bloque JSON, sin texto antes ni después:\n"
    '{{"preguntas": [{{"tema": "forense", "dificultad": "facil", "pregunta": "¿...?", '
    '"respuesta": "...", "dato_extra": "una frase de contexto, opcional", '
    '"texto_pregunta": "versión corta para pantalla", "texto_respuesta": "EN MAYÚSCULAS", '
    '"verificacion": "por qué es correcto y de dónde sale", '
    '"busqueda_pregunta": "english scene", "busqueda_respuesta": "english scene"}}]}}'
)
