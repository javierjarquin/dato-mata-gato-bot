"""Bot de Telegram que puentea la conversación a una sesión de Claude Code
por chat, para dirigir el pipeline de Dato Mata Gato desde el celular.

Flujo por comandos (no todo dispara a Claude):
  /nuevovideo [slug]  -> modo recolección: guarda guion.json e imágenes
                         SIN invocar a Claude, es solo mover archivos.
  /generar            -> el único disparo real a Claude: corre el
                         pipeline completo con todo lo ya recolectado.
  /estatus             -> si hay una generación en curso y desde cuándo.
  /nuevo               -> reinicia la conversación con Claude desde cero.
Los mensajes de texto libres sí siguen la conversación con Claude
(para pedir ajustes después de generar), salvo que haya una generación
en curso.
"""

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, time, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# ANTES que cualquier import de dato_mata_gato_bot.* -- importar esos módulos
# ejecuta su código de nivel de módulo, y si alguno lee una variable de
# entorno ahí (no adentro de una función) queda fija con lo que hubiera
# ANTES de cargar el .env, para siempre (confirmado en una corrida real:
# pipeline.GOOGLE_DRIVE_FOLDER_ID quedaba en "" pese a que el .env sí lo
# tenía, porque el import de pipeline pasaba antes que este load_dotenv()).
load_dotenv()

from telegram import Update  # noqa: E402
from telegram.constants import ParseMode  # noqa: E402
from telegram.ext import (  # noqa: E402
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from dato_mata_gato_bot import (  # noqa: E402
    auto_query,
    avatar_presentador,
    daily_publish,
    formatos,
    lote_grande,
    free_image_search,
    generated_videos,
    banco_preguntas,
    image_naming,
    pipeline,
    publish_schedule,
    revision_guion,
    scrape_poc,
    sessions,
    summary,
    trivia_generator,
    wiki_images,
)
from dato_mata_gato_bot.instruccion_preguntas import INSTRUCCION_PREGUNTAS  # noqa: E402
from dato_mata_gato_bot.claude_runner import es_limite_de_uso, run_turn, tamano_sesion  # noqa: E402
from dato_mata_gato_bot.logging_config import setup_logging  # noqa: E402

logger = logging.getLogger(__name__)

ANDROID_IN = Path(r"C:\Android_in")
TELEGRAM_MSG_LIMIT = 4000
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}

# Catalogo de voces ya exploradas/probadas (ver tts-kokoro/projects/voces_exploracion).
VOICES = (
    "am_adam", "am_santa", "am_onyx", "am_michael", "am_fenrir",
    "bm_george", "pm_santa", "pm_alex", "em_santa", "em_alex", "ef_dora",
)

# Publicación automática diaria: 20:00 hora de México (franja de mayor
# consumo entre semana, elegida por el usuario). Con tzinfo explícito y no
# la hora local del sistema: si la máquina cambiara de zona, la publicación
# se correría sin que nadie se entere.
HORA_PUBLICACION = time(20, 0, tzinfo=ZoneInfo("America/Mexico_City"))

# Desde el 09/09/2026 Javier publica a mano (modalidad de 5 videos por día, que
# el job de a uno no cubre). Queda APAGADA por defecto: con el job vivo, el bot
# publicaría en la Página por su cuenta al lado de lo que sube él. Para
# reactivarla, PUBLICACION_AUTOMATICA=1 en el .env.
PUBLICACION_AUTOMATICA = os.getenv("PUBLICACION_AUTOMATICA", "").strip() == "1"

INSTRUCCION_ESCALAR = (
    "El pipeline automático (sin Claude) corrió para '{slug}' y se quedó trabado. NO des "
    "por hecho en qué paso: fijate qué hay en disco antes de tocar nada. Esto es lo que "
    "reportó:\n\n{detalle}\n\n"
    "SI FALTA EL AUDIO (no existe projects/{slug}/narracion.wav, o falta algún plano en "
    "C:\\tts-kokoro\\projects\\{slug}\\narracion\\): regeneralo SIEMPRE con el comando del "
    "pipeline, nunca a mano ni con otra voz:\n"
    "C:\\dato-mata-gato-bot\\.venv\\Scripts\\python.exe -m dato_mata_gato_bot.regenerar_audio {slug}\n"
    "Eso usa el motor y la voz clonada del canal. Confirmado en una corrida real del "
    "14/09/2026: el contenedor de VoiceStudio estaba caído, este mensaje decía 'audio "
    "generado' cuando no lo había, y el audio salió con una voz distinta en cada plano "
    "-- de 95 a 210 Hz, más de una octava. Un video con cuatro voces no se puede publicar.\n\n"
    "SI EL AUDIO ESTÁ Y EL PROBLEMA ES DE MEDIOS: resolvelo siguiendo CLAUDE.md "
    "(investigar/ajustar busqueda_medios, o ficha de texto si no hay foto real, etc.).\n\n"
    "En cualquier caso, corré narrator generate las veces que haga falta TODO EN "
    "FOREGROUND, y cuando final.mp4 esté listo subilo a Drive vos mismo con:\n"
    "C:\\dato-mata-gato-bot\\.venv\\Scripts\\python.exe -m dato_mata_gato_bot.upload_cli {slug}\n"
    "(desde cualquier carpeta -- ese comando ya arma el nombre progresivo y actualiza el "
    "calendario de publicación solo). Avisame cuando esté listo, o si algo no se puede resolver."
)

INSTRUCCION_NUEVO_LOTE = (
    "Generá {n} guiones NUEVOS de casos reales de true crime mexicano para el canal, "
    "siguiendo el mismo formato de guion.json y el mismo estilo/tono que los guiones ya "
    "hechos. Si necesitás ver el formato, abrí UN SOLO guion.json de ejemplo, no más. "
    "Los casos que ya están cubiertos van en una lista al final de este mensaje: no "
    "repitas ninguno, y no abras los archivos para comprobarlo.\n\n"
    "Para cada uno de los {n}:\n"
    "1. Elegí un slug corto en minúsculas con guiones (ej. guion-nombre-caso).\n"
    "   TRES CAMPOS DISTINTOS, y no hay que mezclarlos (cambio del 17/09/2026):\n"
    "   - \"titulo\": el NOMBRE del caso, corto. \"Caso Paulette\", \"Caso Durazno\", "
    "\"Villas de Salvárcar\". MÁXIMO 30 CARACTERES. Sirve para nombrar el archivo y "
    "para el calendario de publicación, no para narrar. Antes el título era también "
    "la primera frase hablada y por eso salían de dos oraciones (105 caracteres en "
    "guion-villas-de-salvarcar); ya no: el título nombra, no cuenta.\n"
    "   - \"gancho\": el texto GRANDE que aparece en pantalla los primeros segundos. "
    "MÁXIMO 35 CARACTERES, 3 a 5 palabras. No es el título ni un resumen: es el "
    "golpe. Ejemplos: \"LOS MATÓ LA POLICÍA\", \"PAGARON EL RESCATE\", \"NADIE FUE "
    "DETENIDO\". Los dos van en la RAÍZ del guion.json.\n"
    "   - La primera frase de p00 es el gancho HABLADO, y se explica abajo.\n"
    "2. Escribí el guion.json completo (planos, narración, visual, etc.) con los HECHOS "
    "REALES del caso -- si no estás seguro de un dato puntual, no lo inventes.\n"
    "   IMPORTANTE, formato de apertura (27/08/2026, ver CLAUDE.md): los guiones ya "
    "NO llevan plano de identidad al arranque. NO generes ningún plano con "
    "seccion=\"identidad_apertura\" ni con el logo del canal sobre negro. El p00 es "
    "directamente el primer plano de CONTENIDO, para que el gancho se escuche desde el "
    "segundo cero -- confirmado con prueba A/B real que la tarjeta de logo al inicio le "
    "comía ~4.7s a la ventana de retención.\n"
    "   EL GANCHO HABLADO VA SOLO EN p00, Y ES CORTO (cambio del 17/09/2026). p00 es UNA "
    "SOLA FRASE (o dos muy cortas): el dato más fuerte del caso, el más indignante o "
    "incomprensible. MÁXIMO 12 PALABRAS, unos 4 segundos (cambio del 11/10/2026: con 18 "
    "palabras y fecha dicha, el dato llegaba hacia el segundo 7 y el usuario sintió los "
    "ganchos débiles; en la prueba de oído ganaron los de 12). Reglas del gancho:\n"
    "   - El dato que duele va PRIMERO, no después de quién, cuándo y dónde.\n"
    "   - NINGÚN AÑO NI FECHA DICHOS en p00: \"mil novecientos setenta y cuatro\" son seis "
    "palabras sin dato. La fecha va en texto_en_pantalla o en p01.\n"
    "   - Que tenga una contradicción o algo que no se explica: \"Frank Sinatra ofreció un "
    "millón por su hijo. Los secuestradores pidieron menos.\"\n"
    "   Ejemplos: \"Los mataron en una fiesta de cumpleaños. El presidente dijo que eran "
    "pandilleros.\" \"La policía entró a su granja y encontró una lámpara hecha con piel "
    "humana.\"\n"
    "   El CONTEXTO va en p01 y no en p00. El motivo es medido: en "
    "guion-villas-de-salvarcar p00 duraba 17.7 segundos, el 21% del video, porque "
    "mezclaba el gancho con la inmersión. Un gancho es una frase corta y clara; lo que "
    "se extiende es el contexto, que viene después.\n"
    "   FÓRMULA DEL p01 (cambio del 20/09/2026). Se abandona la segunda persona "
    "(\"Eres estudiante de preparatoria...\"): ahora p01 abre SEÑALANDO AL PERSONAJE, "
    "narrado en TERCERA PERSONA y en PASADO.\n"
    "   La primera frase es: \"Te imaginas a [quién] que en [cuándo, dónde] [qué hizo o "
    "qué encontró]\". Ejemplos:\n"
    "   - \"Te imaginas al chatarrero que abrió a golpes esa cápsula de metal en "
    "Goiânia, Brasil, en septiembre de 1987.\"\n"
    "   - \"Te imaginas a José Benítez y a sus amigos de Playa Vicente, que en enero de "
    "2016 fueron detenidos por la Policía Estatal en Tierra Blanca, Veracruz.\"\n"
    "   - \"Te imaginas al chatarrero Devair Alves Ferreira, que en septiembre de 1987 "
    "vio brillar de azul el polvo de una cápsula en Goiânia, Brasil.\"\n"
    "   Reglas, y son estrictas:\n"
    "   a) NUNCA \"eres\", \"te llevas\", \"lo abres\". Si después del \"te imaginas a\" "
    "aparece un verbo en segunda persona, está mal.\n"
    "   b) Al personaje se lo nombra con NOMBRE Y APELLIDO, más su rol (el chatarrero "
    "Devair Alves Ferreira). Ver NOMBRES, abajo.\n"
    "   c) El \"te imaginas a\" va UNA SOLA VEZ, al inicio de p01. No se repite en p02 "
    "ni en p03.\n"
    "   d) El resto de p01 sigue en tercera persona y en pasado: \"no había visto algo "
    "parecido, así que repartió pedazos\".\n"
    "   NOMBRES (cambio del 28/09/2026, decisión del usuario). Se acaba la regla de no "
    "usar nombres. Es la queja que más le hace la audiencia al canal: sin nombres, el "
    "caso suena a cuento y no a true crime. Y además es lo que dejaba los videos sin "
    "evidencia real: la búsqueda de fotos del caso busca por los nombres del guion, y en "
    "el lote del 26/09 hubo guiones sin UN SOLO nombre propio (Tierra Blanca decía \"un "
    "vocero estatal\", \"un comandante\", \"los jóvenes\"): 16 de 18 videos salieron "
    "con todas las imágenes hechas por IA.\n"
    "   Todo guion NOMBRA, con nombre y apellido tal como salió en la prensa:\n"
    "   - a las VÍCTIMAS;\n"
    "   - el LUGAR exacto: municipio o colonia Y estado (\"Tierra Blanca, Veracruz\"), "
    "ya en p00 o p01, no solo el país;\n"
    "   - a los FUNCIONARIOS que actuaron: el fiscal, el gobernador, el jefe de policía, "
    "el juez, el vocero (\"el fiscal Luis Ángel Bravo\", no \"un fiscal\");\n"
    "   - a los ACUSADOS y condenados;\n"
    "   - las INSTITUCIONES por su nombre (la Policía Estatal de Veracruz, la Fiscalía "
    "General del Estado), no \"la policía\".\n"
    "   Mínimo: el lugar exacto y TRES nombres de persona por guion. Y cada nombre, "
    "dicho la primera vez completo (Luis Ángel Bravo) y después como suena natural (Bravo).\n"
    "   MÁXIMO DOS NOMBRES POR FRASE. Con cuatro nombres seguidos la voz se come uno "
    "(medido el 28/09/2026: en Tierra Blanca se saltó a \"Mario\", y en otra prueba a "
    "\"José Alfredo González\"). Mal: \"Iba con A, B, C y D.\" Bien: \"Iba con A y B. "
    "También con C y D.\"\n"
    "   NOMBRES QUE LA VOZ NO PUEDE DECIR: los de origen náhuatl que empiezan con "
    "\"Tl\" (Tlalixcoyan, Tlaxiaco, Tlapa) se los salta o los deforma -- probadas siete "
    "escrituras de Tlalixcoyan el 28/09/2026 y fallaron todas. Ese lugar va en "
    "texto_en_pantalla, y en la narración se dice el municipio más cercano o el estado "
    "(\"en el rancho El Limón, también en Veracruz\").\n"
    "   Tres límites, y no son de tono sino de ley:\n"
    "   1) MENORES DE EDAD, víctimas o acusados: no se nombran (la Ley General de los "
    "Derechos de Niñas, Niños y Adolescentes protege su identidad). Excepción: el caso "
    "se conoce públicamente por su nombre (Caso Paulette). Se dice su edad y su rol.\n"
    "   2) ACUSADO NO CONDENADO: se nombra, pero se dice el hecho procesal, no la culpa "
    "como hecho. \"La fiscalía lo acusó de...\", \"lo detuvieron y sigue sin sentencia\", "
    "no \"él los mató\". Sin \"presuntamente\" (regla d de abajo): el hecho procesal "
    "dicho claro reemplaza al adverbio.\n"
    "   3) Si no estás SEGURO de cómo se escribe un nombre o de quién fue, no lo "
    "inventes ni lo adivines: se nombra solo lo que puedas confirmar en una fuente.\n"
    "   El plano de CIERRE (seccion=\"identidad_cierre\") SÍ se mantiene al final, pero "
    "ahora lleva LLAMADO A LA ACCIÓN -- ver abajo.\n"
    "   TONO (cambio del 27/08/2026, decisión del usuario): se elimina la regla vieja de "
    "\"tono contenido, nunca morboso\". Contá los hechos del caso de forma directa y concreta, "
    "sin eufemismos ni rodeos -- si un hecho es brutal, se dice. NO generes reglas de "
    "auto-censura de tono en 'regla_narracion' ni en 'verificar_antes_de_publicar'. La primera "
    "frase de p00 debe ser el dato MÁS FUERTE del caso: el más indignante, incomprensible o "
    "impactante -- el que obliga a quedarse a entender cómo pasó eso.\n"
    "   CÓMO SE ESCRIBE (nuevo, 22/09/2026). Lo de arriba dice QUÉ contar; esto dice "
    "cómo suena. Medido sobre el lote del 22/09: 15 de 20 ganchos remataban a mitad de "
    "frase, 12 de 20 abrían con la misma palabra, la frase más larga de cada guion "
    "tenía entre 30 y 37 palabras, y dos guiones distintos (Metro Línea 12 y Colegio "
    "Rébsamen) CERRABAN CON LA MISMA ORACIÓN. Los datos estaban bien; el lote sonaba a "
    "boletín de prensa y los videos se sentían iguales entre sí.\n"
    "   a) NINGUNA FRASE PASA DE 20 PALABRAS. Si una frase tiene dos ideas, son dos "
    "frases. El punto es el que da el golpe.\n"
    "   b) EL GANCHO TERMINA EN LA PALABRA QUE DUELE. Nada de complementos colgando "
    "después. Mal: \"Un tramo del metro se vino abajo en hora pico, con gente adentro "
    "de los vagones.\" Bien: \"Un tramo del metro se partió en hora pico. Adentro iba "
    "gente.\"\n"
    "   c) EL SUJETO TIENE CARA Y NOMBRE. Prohibido como sujeto: \"la responsabilidad\", "
    "\"las autoridades\", \"el expediente\", \"el caso\", \"la investigación\", \"un "
    "operativo\", \"la institución\", \"los hechos\". Quién hizo qué, con la persona "
    "nombrada: el fiscal Luis Ángel Bravo, la madre de José Benítez, el soldado.\n"
    "   d) NADA DE VERBOS DE VOCERO: \"perdió la vida\" es murió, \"se vino abajo\" es "
    "se cayó, \"resultó con lesiones\" es quedó herido, \"se llevó a cabo\" es se hizo. "
    "Fuera también \"presuntamente\", \"al parecer\", \"se presume\", \"trascendió\".\n"
    "   e) NADA DE CONECTORES DE ENSAYO: \"en cambio\", \"sin embargo\", \"no "
    "obstante\", \"cabe mencionar\", \"por su parte\", \"asimismo\", \"con claridad\", "
    "\"de alguna manera\". Ocupan segundos y no traen un dato.\n"
    "   f) DENTRO DEL LOTE, NINGÚN GANCHO ABRE CON LA MISMA PALABRA QUE OTRO, Y NINGÚN "
    "CIERRE REPITE LA ESTRUCTURA DE OTRO. En particular está quemada la forma \"A; B, "
    "en cambio, C\" -- se usó en 11 de 20. Antes de entregar, leé los {n} ganchos "
    "seguidos y los {n} cierres seguidos: si dos se parecen, reescribí uno.\n"
    "   g) LA NARRACIÓN VA EN ESPAÑOL DE MÉXICO, DE TÚ. Esta instrucción está escrita en "
    "voseo, pero el guion NO: \"Dímelo en los comentarios\", \"¿Crees que...?\", nunca "
    "\"Decímelo\" ni \"¿Creés?\". El canal es mexicano, y el lote del 22/09/2026 salió "
    "con voseo en los 20 cierres.\n"
    "   Se puede verificar antes de generar los videos con:\n"
    "   python C:\\dato-mata-gato-bot\\tools\\medir_tono.py\n"
    "   LARGO (medido el 11/09/2026 sobre el lote del 10/09): los guiones venían saliendo de "
    "92 a 116 segundos, y en vertical corto la tasa de finalización se sostiene por debajo de "
    "los 60-70. La narración se lee a ~170 palabras por minuto, así que el objetivo es "
    "170-200 PALABRAS DE NARRACIÓN EN TOTAL, sumando todos los planos, en 7 u 8 planos. "
    "Es un recorte real: hay que elegir qué dato entra y cuál no, no comprimir todo. Si un "
    "caso no cabe, contá UN ángulo del caso, no el caso entero.\n"
    "   CIERRE EN BUCLE: la última frase del último plano de CONTENIDO tiene que empalmar "
    "con la primera frase de p00, de modo que al repetirse el video se sienta continuo en vez "
    "de terminar. En Shorts el re-visionado es de las señales de distribución más fuertes, y "
    "un cierre que devuelve al arranque lo consigue sin un segundo extra de material. Ejemplo: "
    "si p00 abre con 'Murió en una cirugía para cambiar de cara', el cierre no es 'el caso "
    "quedó sin resolver' sino algo que deja la frase de apertura sonando, tipo 'y nadie "
    "volvió a preguntar de quién era esa cara'. NO repitas la frase de apertura literal: "
    "tiene que empalmar, no ser un eco.\n"
    "   LLAMADO A LA ACCIÓN HABLADO (nuevo, 17/09/2026): el plano de identidad_cierre "
    "tiene que PEDIR algo. Hasta ahora decía solo la firma del canal (\"Aquí el dato mata "
    "al gato... y la historia mata el sueño\") -- 3.2 segundos que no piden nada. Revisados "
    "los 103 guiones del proyecto, NINGUNO tenía llamado a la acción hablado; solo hay una "
    "tarjeta escrita de 2.3s que nadie dice en voz alta.\n"
    "   La narración de identidad_cierre es: la firma del canal + UNA petición concreta, "
    "en 12 a 18 palabras. Pedí UNA sola cosa, no cuatro.\n"
    "   PEDÍ SIEMPRE UN COMENTARIO, no un seguimiento (preferencia del usuario, "
    "17/09/2026). \"Seguime\" quedó descartado: suena a pedir un favor. Preguntar la "
    "opinión invita a participar, y además el comentario es la señal de distribución más "
    "fuerte de las tres -- pesa más que el like y mucho más que el seguir.\n"
    "   La pregunta tiene que ser sobre ESTE caso, no genérica: lo que se pregunta es lo "
    "que el caso deja abierto. Ejemplos: \"Aquí el dato mata al gato. ¿Tú qué opinas? "
    "Cuéntamelo en los comentarios.\" o, mejor todavía porque apunta al nervio del caso, "
    "\"Aquí el dato mata al gato. ¿Le crees a la versión oficial? Dímelo en los "
    "comentarios.\"\n"
    "   OJO, no toca el cierre en bucle: el bucle vive en el ÚLTIMO PLANO DE CONTENIDO "
    "(el de antes) y el llamado a la acción en el de identidad. Son dos planos distintos y "
    "cada uno hace lo suyo -- el bucle empalma con la apertura, y recién después se pide.\n"
    "   VISUALES -- REEMPLAZADO el 29/09/2026 por EVIDENCIA REAL (más abajo): lo que sigue "
    "queda solo como historia de por qué la búsqueda por palabras no funcionaba; no lo "
    "apliques. `visual.busqueda_medios` era en INGLÉS y describía una ESCENA concreta y "
    "fotografiable. Medido el 11/09/2026: las tomas venían saliendo intercambiables "
    "-- 'quirófano vacío', 'carretera vacía', 'pasillo vacío' sirven para cualquier caso, y "
    "eso es lo que separa un canal que investigó de uno que puso stock.\n"
    "   - ANCLÁ AL LUGAR Y A LA ÉPOCA, que es lo que hace la toma de ESTE caso y no de otro: "
    "'Mexico City street 1997', 'Ciudad Juarez border checkpoint 1990s', 'Mexican newspaper "
    "archive 1997' valen mucho más que 'empty hallway'. El material de época no es una "
    "recreación, es documento: no choca con ninguna de las reglas de abajo.\n"
    "   - NUNCA pongas el NOMBRE de una persona real como búsqueda. Además de traer retratos "
    "de la víctima o del acusado (que no se usan), trae cualquier archivo que mencione ese "
    "nombre. Confirmado en una corrida real: buscar por el nombre del caso metió una captura "
    "titulada 'Vandalismo en articulo de...' -- una página de Wikipedia adulterada con datos "
    "de broma -- en 4 de las 5 tomas del cierre de un video. En un canal cuyo lema es "
    "'contamos lo que pasó', eso es lo más caro que se puede mostrar en pantalla. La búsqueda "
    "describe un LUGAR, un OBJETO o una ÉPOCA; nunca a quién.\n"
    "   Excepciones que SÍ se mantienen (no son tono, son riesgo concreto y verificable):\n"
    "   a) De un suicidio o intento se puede contar TODO menos el método concreto: que "
    "ocurrió, cuándo, en qué circunstancias, las secuelas, las señales previas, a quién le "
    "pidió ayuda la persona y cómo fallaron las instituciones -- todo eso se narra sin "
    "recortar. Lo único que se omite es CÓMO lo hizo (el medio o procedimiento), porque el "
    "efecto de contagio por descripción de método está documentado y las plataformas lo "
    "sancionan. No es suavizar el caso: es el único dato que no aporta comprensión. "
    "Esto incluye NO decirlo en clave ni con eufemismos (tipo \"líquido rojo\" por sangre): "
    "el eufemismo no reduce el riesgo -- el método se comunica igual -- las plataformas ya "
    "detectan ese lenguaje, y suena a canal esquivando, que es lo contrario a la autoridad "
    "factual que define a Dato Mata Gato.\n"
    "   b) Caso Ingrid Escamilla y similares: NO describir el contenido de fotografías "
    "filtradas de una víctima. En México la Ley Ingrid penaliza difundir ese material, y ese "
    "caso trata justamente sobre el daño de haberlo difundido.\n"
    "   c) NO generar imágenes de IA que representen a víctimas reales identificables ni "
    "recreaciones de la escena del crimen. Eso no es narrar un hecho, es fabricar material "
    "sobre una persona real. Las imágenes siguen siendo espacios/objetos, sin personas "
    "identificables.\n"
    "   EVIDENCIA REAL (nuevo, 29/09/2026, decisión del usuario): los true crime YA NO "
    "llevan imágenes de IA. Cada guion trae su propia evidencia, y el pipeline la baja y "
    "la arma sin volver a llamarte (dato_mata_gato_bot/evidencia.py). Aprobado con el "
    "video de Tierra Blanca: fotos reales del pueblo, la Recomendación 5VG/2017 de la "
    "CNDH, titulares de prensa y fichas con fuente.\n"
    "   Mientras investigás el caso, anotá de dónde sale cada dato y juntá entre 5 y 10 "
    "piezas. PRESUPUESTO: máximo 8 búsquedas web y 6 páginas abiertas por caso. Van en "
    "la RAÍZ del guion.json como \"evidencia\": [ ... ], cada una con un \"id\" (e1, "
    "e2...) y uno de estos tipos:\n"
    "   - {{\"id\":\"e1\",\"tipo\":\"lugar\",\"wikimedia\":\"File:Palacio Municipal Tierra "
    "Blanca, Veracruz.jpg\"}} -- foto del sitio en Wikimedia Commons. Si no sabés el "
    "archivo exacto, \"buscar_wikimedia\":\"Tierra Blanca Veracruz\" en vez de "
    "\"wikimedia\".\n"
    "   - {{\"id\":\"e2\",\"tipo\":\"persona\",\"wikimedia\":\"File:...jpg\"}} -- SOLO "
    "funcionarios o figuras públicas con foto libre en Wikimedia. NUNCA víctimas, nunca un "
    "acusado sin sentencia, nunca un menor.\n"
    "   - {{\"id\":\"e3\",\"tipo\":\"documento\",\"url\":\"https://...pdf\",\"pagina\":1,"
    "\"fuente\":\"CNDH · Rec. 5VG/2017\"}} -- texto oficial: recomendación de la CNDH, "
    "boletín de fiscalía, sentencia, comunicado de gobierno. PDF (con número de página) o "
    "página web. Los textos administrativos y judiciales no tienen derechos de autor.\n"
    "   - {{\"id\":\"e4\",\"tipo\":\"prensa\",\"url\":\"https://...\",\"fuente\":\"Proceso, "
    "15/03/2019\"}} -- una NOTA de un medio. Se captura solo el titular y la fecha.\n"
    "   - {{\"id\":\"e5\",\"tipo\":\"ficha\",\"titulo\":\"11:37 · Tierra Blanca\","
    "\"renglones\":[\"Una cámara...\"],\"fuente\":\"Milenio\"}} -- un dato escrito, con la "
    "fuente de donde lo sacaste. Para horas, cifras, cronologías y listas de detenidos. "
    "Título de hasta 30 caracteres, renglones cortos.\n"
    "   Y en CADA plano de contenido, \"visual\": {{\"tipo\": \"archivo_historico\", "
    "\"evidencia\": [\"e1\", \"e5\"], ...}}: las piezas que se ven mientras se narra ESE "
    "plano. Lo que se ve tiene que ser lo que se dice: si el plano nombra la "
    "recomendación de la CNDH, va el documento de la CNDH. Una pieza puede repetirse "
    "entre planos.\n"
    "   Reglas: (a) todas las URL tienen que ser de páginas que ABRISTE y existen -- una "
    "URL inventada o rota se cae sola y deja el plano sin evidencia; (b) al menos TRES "
    "piezas que no sean ficha (lugar, persona, documento o prensa); (c) SI UN CASO NO "
    "TIENE ESA EVIDENCIA, NO LO ESCRIBAS: elegí otro. Un caso sin nada verificable es "
    "exactamente lo que suena a cuento; (d) \"busqueda_medios\" y \"prompt_ia\" van "
    "vacíos: ya no se busca ni se genera nada por palabras.\n"
    "3. Guardalo en C:\\Android_in\\<slug>\\guion.json.\n\n"
    "Cuando termines los {n}, respondé ÚNICAMENTE con este bloque JSON, sin texto antes "
    "ni después (se parsea automático):\n"
    '{{"guiones": [{{"slug": "...", "titulo": "...", "resumen_hechos": "..."}}, ...]}}\n'
    "\"resumen_hechos\" es para que el usuario pueda revisar la veracidad sin abrir cada "
    "archivo -- 2-3 líneas con los datos centrales del caso (nombres, fechas, qué pasó)."
)


# Mitos y leyendas (25/09/2026). Sale de los dos POC aprobados por el usuario
# (mito-yum-balam y mito-huay-chivo); la fórmula completa, con el porqué de
# cada regla, está en clip_assistance/analisis/formula_mitos.md.
#
# Está escrita DE TÚ a propósito: la instrucción de crimen está en voseo
# ("Generá", "Elegí") y eso se contagia al guion -- el lote del 22/09 salió
# con "Decímelo" y "¿Creés?" en los 20 cierres. En este formato, que va entero
# en segunda persona ("si caminas", "no voltees"), sería imposible de no notar.
INSTRUCCION_MITO = (
    "Genera {n} guiones NUEVOS de MITOS Y LEYENDAS de América Latina para el canal "
    "Dato Mata Gato. Los mitos que ya están hechos van en una lista al final de este "
    "mensaje: no repitas ninguno. Prioriza leyendas de México, y "
    "sobre todo de la península de Yucatán.\n\n"
    "LA IDEA: no se cuenta la leyenda, se enseña a SOBREVIVIRLA. Primero una guía de "
    "advertencia que mete al espectador en el lugar, y después la revelación de quién "
    "es ese ser, de dónde viene y cómo se le conoce en otros países.\n\n"
    "1. INVESTIGA ANTES DE ESCRIBIR, con búsqueda web. Cada dato del guion sale de una "
    "fuente; ninguno se inventa para que asuste más.\n"
    "   - Prefiere fuentes antropológicas, académicas o de la comunidad (revistas de "
    "universidades, INAH, relatos recogidos en un pueblo con nombre) antes que blogs "
    "de leyendas.\n"
    "   - NO mezcles leyendas. Si un rasgo es de OTRO ser, no va, aunque la versión "
    "popular lo tenga. Ejemplo real: la regla 'si el silbido se oye cerca está lejos, "
    "si se oye lejos está cerca' es del Silbón de los Llanos (Venezuela y Colombia), "
    "NO del Yum Balam de Yucatán.\n"
    "   - Si la versión popular contradice la tradición, GANA LA TRADICIÓN, y se cuenta "
    "como el giro del video. Ejemplo real: el Yum Balam no acecha, protege; su chiflido "
    "es para que te calles.\n"
    "   - Pon las fuentes en el campo \"fuentes\" del guion, y cada afirmación en "
    "\"verificar_antes_de_publicar\".\n"
    "   - PRESUPUESTO DE INVESTIGACIÓN, por mito: máximo 6 búsquedas web y 5 páginas "
    "abiertas. No descargues ni leas PDFs completos. Cada página que abres se queda en "
    "el contexto de todos los pasos que siguen: la prueba de la Xtabay hizo 92 pasos y "
    "gastó 10 millones de tokens. Con 3 o 4 fuentes buenas alcanza.\n\n"
    "2. LA ESTRUCTURA.\n"
    "   A) ADVERTENCIA, de TÚ (segunda persona):\n"
    "      - p00, seccion \"gancho_hablado\": una frase de máximo 18 palabras. \"Si "
    "[haces algo] por [un lugar real] [a cierta hora], hay [N] señales que no puedes "
    "ignorar.\"\n"
    "      - Las señales: LAS QUE DOCUMENTE LA TRADICIÓN de ese ser, de 2 a 4. No "
    "rellenes con señales inventadas para llegar a un número; la apertura dice el "
    "número real. Cada señal son DOS planos:\n"
    "        * seccion \"senal_1\" (\"senal_2\", ...): lo que se oye, se ve o se siente. "
    "Corto: \"La primera: un chiflido fuerte, muy cerca de ti.\" Lleva "
    "\"pausa_despues_seg\" entre 1.5 y 2.2, en el PLANO (al lado de \"narracion\", no "
    "dentro de \"audio\"): en ese silencio SUENA lo que se nombró.\n"
    "        * seccion \"significado_1\" (...): lo que quiere decir, según la tradición.\n"
    "      - La mejor señal es la que contradice lo que el espectador espera.\n"
    "   B) REVELACIÓN, de ÉL (tercera persona), en este orden:\n"
    "      - quién es y qué significa su nombre;\n"
    "      - cómo lo describe la tradición;\n"
    "      - su historia: el origen, el texto antiguo, de dónde viene el nombre;\n"
    "      - en otros países: seres PARECIDOS de otras culturas. Se dicen parecidos, "
    "NUNCA 'el mismo con otro nombre'. Si no tiene parientes claros, esta parte SE "
    "SALTA -- no fuerces un parecido lejano;\n"
    "      - la tradición viva: cómo se le respeta hoy (ofrendas, rezos). Va justo "
    "antes del lado oscuro, porque es su causa.\n"
    "   C) LADO OSCURO (seccion \"lado_oscuro\"): uno o dos RELATOS DOCUMENTADOS, con el "
    "lugar donde se cuentan, narrados como relatos (\"en Tihosuco cuentan...\"), no "
    "como hechos. Se cuenta lo que dicen los relatos, NO lo que suena más a terror: si "
    "dicen que castiga al que no le lleva ofrendas, no le agregues 'y te lleva si "
    "andas de madrugada'. Si el ser no tiene relatos oscuros documentados, se salta.\n"
    "   D) CIERRE EN BUCLE (seccion \"cierre_caso\"): vuelve a la advertencia y termina "
    "con el sonido de la leyenda, lejos. Lleva pausa_despues_seg.\n"
    "   E) LLAMADO (seccion \"identidad_cierre\", último plano): \"Aquí el dato mata al "
    "gato.\" + una pregunta que invite a contar lo propio, de tú: \"¿En tu tierra, "
    "quién cuida el monte? Cuéntamelo en los comentarios.\"\n\n"
    "3. CÓMO SUENA.\n"
    "   - ESPAÑOL DE MÉXICO, DE TÚ: si caminas, escuchas, no voltees, cuéntamelo. "
    "NUNCA voseo (caminás, escuchás, tenés, mirá, decímelo, contame).\n"
    "   - Ninguna frase pasa de 20 palabras. El gancho termina en la palabra que duele.\n"
    "   - Largo: unas 300 palabras de narración, unos 2 minutos, hasta 2:30 con el lado "
    "oscuro. Si una sección se salta, el video queda más corto: no se rellena.\n"
    "   - \"titulo\": el nombre del ser, máximo 30 caracteres (\"El Huay Chivo\"). "
    "\"gancho\": 3 a 5 palabras en forma de orden o advertencia, máximo 35 caracteres "
    "(\"NO LO MIRES A LOS OJOS\"). Los dos en la raíz del guion.json.\n"
    "   - Nombres de lugares en maya u otras lenguas que la voz no sabe pronunciar "
    "(Xocén, Oxkutzcab, Tekax): van en el rótulo de pantalla, no en la narración.\n\n"
    "4. EL SONIDO, en \"audio.sfx\" de cada plano. Describe lo que el espectador OYE, "
    "con su distancia (\"cerca\" o \"a lo lejos\"): cerca suena fuerte y seco, lejos "
    "suena bajo, sin agudos y con eco. SOLO estas palabras suenan; cualquier otra sale "
    "muda:\n"
    "   - de fondo, debajo de la voz: grillos, monte, selva, viento, lluvia, latido del "
    "corazón, olas, fuego, retumbo;\n"
    "   - en la pausa, después de la voz: silbido o chiflido, canto de pájaros, ramas u "
    "hojas que se mueven, pasos, tecolote o lechuza, aullido, llanto o lamento, "
    "respiración.\n"
    "   - El silencio también es sonido: \"los grillos se callan\" o \"el canto de "
    "pájaros se corta\" corta ESE sonido y deja el resto.\n"
    "   Ejemplo: \"grillos del monte y un chiflido fuerte cerca\".\n\n"
    "5. LA IMAGEN. Todas \"visual.tipo\": \"imagen_ia\" y \"busqueda_medios\": \"\" "
    "(un mito no tiene fotos de archivo: la búsqueda por nombre trae mapas y ciudades). "
    "\"prompt_ia\" en INGLÉS, describiendo una escena concreta.\n"
    "   - El ser se MUESTRA solo si la tradición lo describe como una FIGURA HUMANA "
    "VESTIDA (el anciano de barba larga, sombrero de palma y túnica): en esos planos "
    "pon \"personaje\": true dentro de \"visual\", y en el prompt \"face shadowed by the "
    "hat brim\" o similar.\n"
    "   - Si es una CRIATURA (mitad animal, peluda, deforme) o un NIÑO: NO se dibuja su "
    "cuerpo. Se muestran sus señales: sus huellas, sus ojos como brasas en la "
    "oscuridad, sus cuernos contra la luna, el corral vacío. Visto en los POC: "
    "\"pequeño, peludo y descalzo\" salió como figuras humanas desnudas.\n"
    "   - En los prompts NO uses la palabra \"eyes\" (arrastra una cara: usa \"glowing "
    "red embers\") ni \"silhouette\" para un personaje (le oscurece toda la ropa).\n"
    "   - LA IMAGEN NO PUEDE CONTRADECIR LA NARRACIÓN. Si el relato habla de un rasgo "
    "del cuerpo que el modelo no sabe dibujar (tres dedos, pies al revés, un ojo de "
    "más), NO muestres esa parte: el modelo dibuja una mano normal de cinco dedos "
    "mientras la voz dice \"tiene tres dedos\" (visto en mito-xtabay). Muestra algo que "
    "lo evoque: la tela del huipil enganchada en una espina, la escarcha en la raíz. "
    "Y si la voz dice \"no te la deja ver\", en pantalla no se ve.\n"
    "   - Evita \"leading away into darkness\" en un camino: el modelo lo resuelve como "
    "un pasillo con una puerta de luz al fondo. Pon el camino con cielo abierto.\n"
    "   - Los seres PEQUEÑOS (aluxes, duendes) el modelo los dibuja como NIÑOS, aunque "
    "pidas una figura de barro: en mito-aluxes \"clay figure wearing a hat\" salió como "
    "una niña con sombrero. Si hace falta un objeto, que sea inconfundible: "
    "\"terracotta statuette, cracked fired clay, close-up of the object\". Y nunca "
    "\"child-sized\" (trajo piernas de adulto): di \"the size of a thumb\".\n"
    "   - Una imagen que no es el ser no lo reemplaza: si el ser es un venado, no pongas "
    "una iguana.\n"
    "   - Nada de sangre ni violencia gráfica, y nada de violencia contra niños aunque "
    "el relato la tenga.\n\n"
    "6. EL ARCHIVO. slug que empiece con \"mito-\" (ej. mito-huay-chivo). En la raíz del "
    "guion.json: \"formato\": \"mito\" -- sin esto el pipeline busca fotos de archivo "
    "por los nombres del guion y llena el video de mapas. Mismo esquema de planos que "
    "los guiones de crimen (id, seccion, narracion, visual, texto_en_pantalla, audio). "
    "El \"texto_en_pantalla\" de cada señal es \"SEÑAL 1 · [LA SEÑAL]\". Guárdalo en "
    "C:\\Android_in\\<slug>\\guion.json.\n\n"
    "Cuando termines los {n}, responde ÚNICAMENTE con este bloque JSON, sin texto antes "
    "ni después (se parsea automático):\n"
    '{{"guiones": [{{"slug": "...", "titulo": "...", "resumen_hechos": "..."}}, ...]}}\n'
    "\"resumen_hechos\" es para que el usuario revise sin abrir cada archivo: 2-3 líneas "
    "con qué es el ser, de dónde es la leyenda, y las fuentes principales."
)


def _load_allowed_ids() -> set[int]:
    raw = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


ALLOWED_CHAT_IDS = _load_allowed_ids()


def _authorized(chat_id: int) -> bool:
    return chat_id in ALLOWED_CHAT_IDS


async def _reject_unauthorized(update: Update) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Este chat no está autorizado todavía.\n\nTu chat_id es: `{chat_id}`\n\n"
        f"Agrégalo a TELEGRAM_ALLOWED_CHAT_IDS en el .env del bot y reinícialo.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _send_long(update: Update, text: str) -> None:
    if not text:
        text = "(sin salida)"
    for i in range(0, len(text), TELEGRAM_MSG_LIMIT):
        await update.message.reply_text(text[i : i + TELEGRAM_MSG_LIMIT])


# Arriba de esto, la conversación del chat con Claude se rota sola. 4 MB de
# historial son unos 200.000 tokens de contexto que se releen en CADA paso; la
# del 26/09/2026 llegó a 16 MB (~900.000) y cada mensaje costaba una fortuna.
_MAX_SESION_CHAT = 4 * 1024 * 1024


async def _dispatch_to_claude(update: Update, message: str) -> None:
    chat_id = update.effective_chat.id
    session_id, is_new = sessions.ensure_session_id(chat_id)
    if not is_new and tamano_sesion(session_id) > _MAX_SESION_CHAT:
        mb = tamano_sesion(session_id) // (1024 * 1024)
        sessions.nueva_sesion_claude(chat_id)
        session_id, is_new = sessions.ensure_session_id(chat_id)
        await update.message.reply_text(
            f"Empiezo una conversación nueva con Claude: la anterior ya pesaba {mb} MB, "
            "y cada mensaje le hacía releer todo ese historial. Lo importante está en "
            "los archivos, no se pierde nada."
        )
    sessions.set_generating(chat_id, True)
    try:
        result = await asyncio.to_thread(run_turn, session_id, message, is_new)
        await _send_long(update, result.text)
    finally:
        sessions.set_generating(chat_id, False)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text.strip())


HELP_TEXT = """Comandos disponibles — flujo típico: /nuevovideo → mandar guion.json → (opcional: fotos/logo/voz) → /generar

/nuevovideo [slug]
  Empieza un capítulo nuevo. Sin slug, se deriva del nombre del archivo que mandes después.
  Ejemplo: /nuevovideo elchalequero
  Después: mandale el guion.json como documento adjunto (no como texto pegado).

/generar
  Corre el pipeline completo (audio + video) para el proyecto actual. Primero intenta
  todo por código; si algo queda ambiguo, recién ahí pide ayuda a Claude.
  Ejemplo: /generar
  Requiere: haber mandado guion.json antes con /nuevovideo.

/lotegrande [cantidad] [tema]
  Con tema (cancun, cdmx, terror, historia, marfil): escribe con la fórmula de
  la contradicción local (te afecta + ahorita + no cuadra + coraje), sin
  presentador. Ejemplo: /lotegrande 5 cancun
  Sin tema: escribe un lote GRANDE y variado (default 30). A diferencia de /lote, reparte
  entre los seis formatos de crimen + trivia, para que el canal deje de abrir
  siempre igual: clásico, caso famoso con ángulo desconocido, caso abierto para
  teorizar, versión oficial contra la evidencia, dato de 15 segundos, y
  culpable/inocente con votación.
  Solo escribe los guiones. Generarlos es /generargrande.
  Ejemplo: /lotegrande        /lotegrande 15

/generargrande
  Genera el lote grande pendiente y lo ARCHIVA sin publicar: nada va a Drive ni
  al calendario. Quedan en C:\Android_in\lotes\<fecha>\ con el nombre corto
  del caso (villasdesalvarcar.mp4).
  Uno de cada diez lleva presentador, rotando entre los avatares 0, 1 y 2.
  ⏱️ Un lote de 30 ronda las 19 horas. Cierra los juegos antes.
  Ejemplo: /generargrande

/vacamorada [avatar] [slug]
  UN video de crimen de punta a punta: escribe el guion, genera el video y encima
  vas vos presentando desde la esquina (55% del ancho, abajo a la derecha) con los
  labios sincronizados a la narración. Sin el gato: ocupan la misma esquina.
  No hace falta /crimen antes — este comando pide el guion solo.
  El NÚMERO elige el avatar: sin número usa el 0 (el de siempre), /vacamorada 1
  usa el del estudio. Lo que no es número se toma como slug de un guion ya
  escrito, para reintentar sin gastar otra llamada a Claude. El orden da igual.
  ⚠️ No hay pausa para revisar los hechos: te muestra el guion y sigue.
  ⏱️ Suma ~35 minutos a un video normal. Cerrá los juegos antes: si la GPU está
  ocupada, el paso de sincronizado se queda sin memoria de video y falla.
  Ejemplos: /vacamorada     /vacamorada 1     /vacamorada 1 guion-caso-x

/estatus
  Dice si hay algo corriendo ahora y en qué paso va (audio, armado, reintento N, etc.).
  Ejemplo: /estatus

/resumen
  Lista cada plano del guion actual: sección, duración, narración y estado de medios.
  Ejemplo: /resumen
  Requiere: proyecto actual con guion.json ya recibido.

/videos
  Lista el calendario de publicación: qué video, para qué fecha, y si ya se subió
  a Drive o sigue pendiente.
  Ejemplo: /videos

/voz [nombre]
  Sin argumento: muestra la voz actual y la lista completa.
  Con argumento: la cambia para el próximo /generar.
  Ejemplo: /voz am_onyx
  Opciones: am_adam (default), am_santa, am_onyx, am_michael, am_fenrir, bm_george,
  pm_santa, pm_alex, em_santa, em_alex, ef_dora

/logo
  Prepara el bot para recibir el logo del canal — el siguiente mensaje debe ser la
  imagen (adjunta, no un link). Se usa siempre en el plano 0 de todos los videos.
  Ejemplo: /logo, después adjuntar la foto del logo.

/cierre
  Prepara el bot para recibir el cartel de cierre del canal — el siguiente mensaje
  debe ser la imagen (adjunta, no un link). Se usa siempre en el plano final
  (identidad_cierre) de todos los videos, en vez de dejarlo sin resolver (ese plano
  es un logo genérico sobre negro puro — ninguna búsqueda de stock real lo va a
  encontrar nunca).
  Ejemplo: /cierre, después adjuntar la imagen de cierre.

/investigar <url | id de plano | palabras clave>
  Busca imágenes con licencia libre (Wikipedia + Openverse + NASA) y te las manda
  una por una (con fuente, licencia y autor) para que elijas. Con un id de plano
  (ej. p02), arma la búsqueda solo con el título del guion + nombres propios de esa
  narración — no hace falta pasar una URL. Independiente de /generar — si falla,
  solo avisa, no bloquea nada.
  Ejemplos:
    /investigar https://es.wikipedia.org/wiki/Criptografía
    /investigar p02
    /investigar Alan Turing máquina Enigma

/scrapear <url>
  POC suelto, sin relación con el pipeline de Dato Mata Gato: baja las imágenes y
  audios de ESA página (todavía no recorre el resto del sitio) y te manda una
  vista previa acá. Sirve igual para sitios estáticos o SPAs de React.
  Ejemplo: /scrapear https://mi-sitio.com

/crimen [cantidad]
  Le pide a Claude (la misma conversación de este chat) que escriba varios guiones
  nuevos de true crime mexicano, revisando qué casos ya están cubiertos para no
  repetir. No genera ningún video todavía -- te manda título + resumen de hechos de
  cada uno para que revises la veracidad antes de seguir. Default: 5.
  Ejemplo: /crimen 3

/trivia [cantidad]
  Igual que /crimen pero en formato de preguntas: 3 preguntas de cultura general por
  video, con pausa de suspenso, cuenta regresiva 3-2-1 con tic-tac, y cierre pidiendo
  comentarios. Default: 5.
  Ejemplo: /trivia 3

/completarlote
  Si un lote se quedó a medias (por ejemplo, se acabó la cuota de Claude), escribe
  solo lo que faltó y lo suma al mismo lote. El bot te avisa cuándo usarlo.

/lotefish3 [cantidad]
  SOLO true crime en el formato de Tierra Blanca: nombres y lugar exacto, evidencia
  real (fotos del lugar, documentos oficiales, titulares, fichas con fuente) y cero
  imágenes de IA, con la voz de Fish 3 y el logo fijo. Cada guion se revisa antes:
  el que no cumple se corrige una vez o sale del lote. Se generan con /generargrande
  (sin presentador). Default: 10. ~40 min por video.
  Ejemplo: /lotefish3        /lotefish3 20

/mitos [cantidad]
  Mitos y leyendas contados como guía de advertencia: "si caminas por el monte de
  noche, hay tres señales...", con el sonido de cada señal en una pausa, y después
  quién es el ser, su historia, sus parientes en otros países y su lado oscuro.
  Claude investiga cada leyenda con fuentes. Unos 2 minutos por video. Default: 5.
  Ejemplo: /mitos 2

/generarlote
  Corre /generar en cadena para cada guion del último lote (/crimen o /trivia), uno
  detrás del
  otro. Si alguno no termina solo, lo escala a Claude igual que /generar y sigue
  con el resto -- no se traba esperando a que se resuelva ese.
  Ejemplo: /generarlote

/publicarfacebook [slug]
  Publica un video YA GENERADO en la Página de Facebook configurada. Manual a
  propósito -- todavía no se dispara solo desde /generar ni /generarlote, así se
  prueba primero antes de engancharlo. Sin slug, usa el proyecto actual.
  Ejemplo: /publicarfacebook guion-clancy

/publicartiktok [slug]
  Igual que /publicarfacebook pero en TikTok. Mientras la app no esté auditada
  por TikTok, el video queda en modo privado (solo lo ve la cuenta que
  autorizó) -- ver README para el proceso de auditoría.
  Ejemplo: /publicartiktok guion-clancy

/nuevo
  Reinicia la conversación con Claude desde cero (borra la memoria del chat, no tus
  archivos ni proyectos).
  Ejemplo: /nuevo

Enviar una imagen para un plano específico:
  Adjuntá la foto (botón de clip, no como texto) con este texto/caption:
  p1 [inicio] [1]
  p1 = número de plano · [inicio|medio|fin] = posición (informativo) · [N] = índice de toma

/ayuda o /help — vuelve a mostrar este mensaje."""


# Para el menú nativo de Telegram (botón "/" con autocompletado). Telegram
# limita la descripción a un renglón corto -- el detalle completo con
# ejemplos vive en HELP_TEXT (/ayuda).
BOT_COMMANDS = [
    ("nuevovideo", "Empezar un capítulo nuevo [slug opcional]"),
    ("generar", "Correr el pipeline completo del proyecto actual"),
    ("estatus", "Ver si hay algo corriendo y en qué paso va"),
    ("resumen", "Narración y estado de medios de cada plano"),
    ("videos", "Calendario de publicación (fecha + estado de subida)"),
    ("voz", "Ver o elegir la voz [nombre opcional]"),
    ("logo", "Mandar/actualizar el logo del canal"),
    ("cierre", "Mandar/actualizar el cartel de cierre del canal"),
    ("investigar", "Buscar imágenes libres [url, plano o palabras clave]"),
    ("scrapear", "POC: bajar imágenes/audio de una página [url]"),
    ("lote", "Lote MIXTO de guiones: crimen + trivia [cantidad]"),
    ("shorts", "Trocear un video en clips de 1 min y subirlos a Drive [url]"),
    ("vacamorada", "Video de crimen con vos presentando [número de avatar opcional]"),
    ("crimen", "Lote de guiones de true crime [cantidad]"),
    ("trivia", "Lote de guiones de trivia/preguntas [cantidad]"),
    ("lotefish3", "Lote de true crime con evidencia real y voz Fish 3 [cantidad]"),
    ("mitos", "Lote de mitos y leyendas [cantidad]"),
    ("completarlote", "Escribir lo que faltó del último lote (si se acabó la cuota)"),
    ("generarlote", "Generar los videos del último lote"),
    ("lotegrande", "Lote grande [cantidad] [tema: cancun, cdmx...]"),
    ("generargrande", "Generar el lote grande y archivarlo sin publicar"),
    ("pausa", "Pausar el lote y liberar la GPU (/pausa ya = cortar el video actual)"),
    ("reanudar", "Seguir el lote donde quedó"),
    ("publicarfacebook", "Publicar un video ya generado en Facebook [slug]"),
    ("publicartiktok", "Publicar un video ya generado en TikTok [slug]"),
    ("nuevo", "Reiniciar la conversación con Claude"),
    ("ayuda", "Ver todos los comandos con ejemplos"),
]


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update.effective_chat.id):
        await _reject_unauthorized(update)
        return
    await _send_long(update, HELP_TEXT)


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update.effective_chat.id):
        await _reject_unauthorized(update)
        return
    await _send_long(update, HELP_TEXT)


async def cmd_nuevovideo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = _slugify(" ".join(context.args)) if context.args else None
    sessions.start_collection(chat_id, slug)

    if slug:
        (ANDROID_IN / slug).mkdir(parents=True, exist_ok=True)
        await update.message.reply_text(
            f"Listo, proyecto '{slug}'. Mándame el guion.json de este capítulo."
        )
    else:
        await update.message.reply_text(
            "Listo, capítulo nuevo. Mándame el guion.json (el slug sale del "
            "nombre del archivo o del texto que le pongas)."
        )


async def cmd_generar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text("No sé de qué proyecto — usa /nuevovideo primero.")
        return

    guion_path = ANDROID_IN / slug / "guion.json"
    if not guion_path.exists():
        await update.message.reply_text(f"Todavía no tengo el guion.json de '{slug}'.")
        return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Ya hay una generación corriendo desde {since}.")
        return

    voz = sessions.get_voice(chat_id)
    await update.message.reply_text(
        f"Arrancando el pipeline para '{slug}' con voz '{voz}' — primero sin Claude "
        f"(más rápido y sin costo). Puede tardar varios minutos. /estatus para ver el paso."
    )

    sessions.set_generating(chat_id, True)
    try:
        result = await asyncio.to_thread(pipeline.run, slug, voz, chat_id)
    finally:
        sessions.set_generating(chat_id, False)
        sessions.set_progress(chat_id, None)

    if result.ok:
        await update.message.reply_text(result.mensaje)
        sessions.set_phase(chat_id, sessions.PHASE_IDLE)
        return

    if not result.necesita_claude:
        await update.message.reply_text(f"Falló: {result.mensaje}")
        return

    await update.message.reply_text(
        f"El pipeline automático no pudo terminar solo:\n{result.mensaje}\n\n"
        f"Paso esto a Claude para que lo investigue y resuelva..."
    )
    await _dispatch_to_claude(update, INSTRUCCION_ESCALAR.format(slug=slug, detalle=result.mensaje))
    sessions.set_phase(chat_id, sessions.PHASE_IDLE)


_LOTE_DEFAULT = 5
# Un lote grande son 30 videos variados que se archivan sin publicar; ver
# lote_grande.py para por qué es un modo aparte y no un lote largo.
_LOTE_GRANDE_DEFAULT = 30


def _parse_lote_response(texto: str) -> list[dict] | None:
    """Lista de guiones de la respuesta de Claude, o None si no hay ninguna.

    Se pide que responda SOLO el bloque JSON, pero no siempre obedece: a veces
    lo envuelve en ```json ... ```, y a veces le antepone o le agrega una
    frase. Antes se exigía que el texto ENTERO fuera JSON, así que cualquier
    palabra de más tiraba el lote abajo -- confirmado en una corrida real del
    12/09/2026: Claude escribió los dos guiones en disco y el lote igual se
    dio por fallido, sin segundo tramo y sin pending_batch, porque su
    respuesta final no era JSON puro.

    Ahora se busca el objeto JSON DENTRO del texto, venga como venga.
    """
    for candidato in _bloques_json(texto):
        try:
            data = json.loads(candidato)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("guiones"), list):
            return data["guiones"]
    return None


def _bloques_json(texto: str):
    """Fragmentos que podrían ser el objeto JSON, del más probable al menos.

    Primero el texto pelado (el caso obediente), después cada bloque entre
    llaves balanceadas -- del último al primero, porque el bloque pedido va
    al final de la respuesta.
    """
    limpio = texto.strip()
    if limpio.startswith("```"):
        limpio = limpio.strip("`").strip()
        if limpio.lower().startswith("json"):
            limpio = limpio[4:].strip()
    yield limpio

    inicios: list[int] = []
    bloques: list[str] = []
    for i, ch in enumerate(texto):
        if ch == "{":
            inicios.append(i)
        elif ch == "}" and inicios:
            arranque = inicios.pop()
            if not inicios:  # se cerró un objeto de nivel superior
                bloques.append(texto[arranque:i + 1])
    yield from reversed(bloques)


CRIMEN = "crimen"
TRIVIA = "trivia"


def _reparto_mixto(n: int) -> list[tuple[str, str, int]]:
    """Cómo se reparte un lote mixto entre crimen y trivia.

    El tipo que va atrás en el calendario se lleva la parte grande, así que
    los lotes alternan solos (3+2, después 2+3, ...) y el canal queda parejo
    aunque un lote se genere a medias.
    """
    if n <= 1:
        return [(CRIMEN, "de true crime", n)]
    cuenta = publish_schedule.contar_por_tipo()
    crimen = (n + 1) // 2 if cuenta["crimen"] <= cuenta["trivia"] else n // 2
    tramos = [(CRIMEN, "de true crime", crimen), (TRIVIA, "de trivia", n - crimen)]
    return [t for t in tramos if t[2] > 0]


def _rellenar_banco(faltan: int, session_id: str, is_new: bool) -> str:
    """Le pide a Claude preguntas para `faltan` temas nuevos y las carga.

    Ocurre DENTRO del lote, no como paso aparte: el banco es un caché de
    preguntas, no un trámite. La verificación del usuario pasa por la revisión
    del lote, igual que con los guiones de crimen.
    """
    por_tema = trivia_generator.PREGUNTAS_POR_DEFECTO
    try:
        banco = trivia_generator.cargar_banco()
        ya_estan = ", ".join(sorted(banco)) or "ninguno"
    except Exception:  # noqa: BLE001 -- banco vacío o inexistente
        ya_estan = "ninguno"

    resultado = run_turn(
        session_id,
        INSTRUCCION_PREGUNTAS.format(temas=faltan, por_tema=por_tema, ya_estan=ya_estan),
        is_new,
    )
    if not resultado.ok:
        logger.error("No pude pedir preguntas nuevas: %s", resultado.text[:2000])
        return ""

    propuestas = _parse_preguntas_response(resultado.text)
    if not propuestas:
        logger.error("Preguntas nuevas sin JSON parseable:\n%s", resultado.text[:4000])
        return ""

    guardadas = banco_preguntas.agregar(propuestas)
    logger.info("Banco de trivias: %d pregunta(s) nuevas", guardadas)
    return f"{guardadas} pregunta(s) nuevas al banco" if guardadas else ""


def _generar_trivias(cantidad: int, session_id: str, is_new: bool) -> tuple[list[dict], str]:
    """Las trivias del lote: salen del banco, y si no alcanza se rellena solo.

    El guion NO lo escribe Claude -- es una plantilla sobre preguntas ya
    cargadas. Claude solo aparece si faltan preguntas, y solo para proponerlas.
    """
    por_video = trivia_generator.PREGUNTAS_POR_DEFECTO
    avisos = []
    try:
        _, _, listos = _temas_listos(por_video)
    except Exception as exc:  # noqa: BLE001 -- el lote sigue con lo de crimen
        logger.error("No pude leer el banco de preguntas: %s", exc)
        return [], f"No pude leer el banco de preguntas ({exc})."

    if len(listos) < cantidad:
        nota = _rellenar_banco(cantidad - len(listos), session_id, is_new)
        if nota:
            avisos.append(nota)
        try:
            _, _, listos = _temas_listos(por_video)
        except Exception as exc:  # noqa: BLE001
            logger.error("No pude releer el banco: %s", exc)

    posibles = min(cantidad, len(listos))
    if not posibles:
        avisos.append("El lote va sin trivias: no hay preguntas suficientes en el banco.")
        return [], " ".join(avisos)

    slugs = trivia_generator.generar(posibles, ANDROID_IN, preguntas=por_video)
    guiones = []
    for slug in slugs:
        datos = json.loads((ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
        guiones.append({
            "slug": slug,
            "titulo": datos.get("titulo", slug),
            # El resumen son las preguntas con su respuesta: es lo que el
            # usuario revisa del lote, igual que los hechos de un caso.
            "resumen_hechos": " | ".join(
                f"{p['narracion']} {s['narracion']}"
                for p, s in zip(
                    [x for x in datos["planos"] if x.get("seccion") == "pregunta"],
                    [x for x in datos["planos"] if x.get("seccion") == "respuesta"],
                )
            ),
        })

    if posibles < cantidad:
        avisos.append(f"Salieron {posibles} de las {cantidad} trivias pedidas.")
    return guiones, " ".join(avisos)


def _parse_preguntas_response(texto: str) -> list[dict] | None:
    """La lista `preguntas` de la respuesta de Claude, venga como venga.

    Mismo criterio que _parse_lote_response: se busca el objeto DENTRO del
    texto en vez de exigir que la respuesta entera sea JSON. Un lote se cayó
    entero por eso el 12/09.
    """
    for candidato in _bloques_json(texto):
        try:
            data = json.loads(candidato)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("preguntas"), list):
            return data["preguntas"]
    return None


def _temas_listos(preguntas_por_video: int) -> tuple[dict, set, list[str]]:
    """Banco, preguntas ya usadas, y temas que alcanzan para un video entero."""
    banco = trivia_generator.cargar_banco()
    usadas = trivia_generator.cargar_usadas()
    return banco, usadas, trivia_generator.temas_disponibles(banco, usadas, preguntas_por_video)


async def cmd_lote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lote MIXTO (crimen + trivia), que es la modalidad actual del canal.
    Uso: /lote [cantidad]"""
    await _pedir_lote(update, context, _reparto_mixto)


async def cmd_lotegrande(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Escribe un lote grande y variado. Uso: /lotegrande [cantidad] (default 30)

    Solo ESCRIBE los guiones; generarlos es /generarlote, igual que siempre,
    para que se puedan revisar antes de gastar once horas de máquina.
    """
    from dato_mata_gato_bot import instruccion_cercania

    temas = {clave: nombre for clave, nombre, _ in instruccion_cercania.TEMAS}
    n, tema = _LOTE_GRANDE_DEFAULT, None
    for arg in context.args or []:
        if arg.isdigit():
            n = int(arg)
        elif arg.lower() in temas:
            tema = arg.lower()
        else:
            await update.message.reply_text(
                "Uso: /lotegrande [cantidad] [tema] (default 30, variado)\n"
                f"Temas con la fórmula de cercanía: {', '.join(temas)}")
            return
    if tema:
        # Con tema (13/10/2026): la fórmula de la contradicción local, la misma
        # de la fábrica, escrita en la sesión ligera. Sin presentador.
        await _pedir_lote(update, context,
                          lambda k: [(f"{CERCANIA}{tema}", f"de {temas[tema]} (fórmula de cercanía)", k)],
                          cantidad=n, sin_avatar=True)
        return
    await _pedir_lote(update, context, formatos.repartir, cantidad=n)


# Tramo "cercania:<tema>" de /lotegrande (fórmula de la contradicción local).
CERCANIA = "cercania:"

_LOTE_FISH3_DEFAULT = 10


async def cmd_lotefish3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lote SOLO de true crime con evidencia real. Uso: /lotefish3 [cantidad] (default 10)

    El formato aprobado con Tierra Blanca (28-29/09/2026): nombres y lugar
    exacto, evidencia real en vez de IA, voz de Fish 3 y logo fijo en vez del
    gato. Escribe los guiones (revisados por revision_guion); se generan con
    /generargrande, que para este lote no pone presentador.
    """
    n = _LOTE_FISH3_DEFAULT
    if context.args:
        try:
            n = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                f"Uso: /lotefish3 [cantidad] (default {_LOTE_FISH3_DEFAULT})")
            return
    await _pedir_lote(update, context, formatos.repartir_fish3, cantidad=n, sin_avatar=True)


async def cmd_crimen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lote de guiones de true crime mexicano. Uso: /crimen [cantidad]"""
    await _pedir_lote(update, context, lambda n: [(CRIMEN, "de true crime", n)])


async def cmd_trivia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lote de trivias armadas desde el banco de preguntas. Uso: /trivia [cantidad]"""
    await _pedir_lote(update, context, lambda n: [(TRIVIA, "de trivia", n)])


async def cmd_completarlote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Escribe los tramos que no salieron del último lote y los suma al mismo lote.

    Pasó el 26/09/2026: un /lotegrande de 20 se quedó sin cuota de Claude
    después de 13 guiones, y no había forma de pedir solo los 7 que faltaban
    -- volver a correr /lotegrande escribía 20 nuevos y tiraba los 13.
    """
    faltan = sessions.get_tramos_faltantes(update.effective_chat.id)
    if not faltan:
        await update.message.reply_text("No hay nada pendiente de escribir en el último lote.")
        return
    total = sum(c for _, _, c in faltan)
    await _pedir_lote(update, context, lambda _n: faltan, cantidad=total, acumular=True)


async def cmd_mitos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lote de mitos y leyendas: guía de advertencia + revelación. Uso: /mitos [cantidad]

    Igual que /crimen y /trivia: Claude investiga y escribe los guiones, el bot
    te los manda para revisar, y recién después se generan con /generarlote.
    La revisión importa el doble acá: una leyenda mezclada con otra (la regla
    del silbido cerca/lejos es del Silbón, no del Yum Balam) es el error que
    alguien de ese pueblo va a corregir en los comentarios.
    """
    await _pedir_lote(update, context, lambda n: [(formatos.MITO, "de mitos y leyendas", n)])


async def cmd_shorts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trocea un video ajeno en clips de 1 minuto y los sube a Drive.
    Uso: /shorts <url del video>"""
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    url = context.args[0] if context.args else ""
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text(
            "Uso: /shorts <url del video>\n"
            "Ejemplo: /shorts https://www.youtube.com/watch?v=XXXXXXXXXXX"
        )
        return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Ya hay algo corriendo desde {since}.")
        return

    # Antes de bajar nada: cuántos trozos van a salir. Una película de hora y
    # media son ~73 trozos y más de 3 GB a Drive, y el usuario tiene que poder
    # cancelar sabiéndolo, no enterarse una hora después.
    info = await asyncio.to_thread(pipeline.info_video_a_trocear, url)
    if info:
        minutos = info["duracion_seg"] / 60
        aviso = (
            f"*{info['titulo']}*\n"
            f"{minutos:.0f} min → *{info['trozos']} trozos* de 1 minuto\n"
            f"~{info['trozos'] * 46 / 1000:.1f} GB a subir a Drive"
        )
        if info["trozos"] > 30:
            aviso += "\n\n⚠️ Son muchos. Va a tardar bastante; mandá /estatus para ver el paso."
        await update.message.reply_text(aviso, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            "No pude leer los datos del video de antemano; lo intento igual."
        )

    await update.message.reply_text(
        "Bajando y cortando (corte literal cada minuto, sin elegir momentos). "
        "Después los subo a Drive."
    )
    sessions.set_generating(chat_id, True)
    try:
        resultado = await asyncio.to_thread(
            pipeline.trocear_y_subir, url,
            lambda paso: sessions.set_progress(chat_id, paso),
        )
    finally:
        sessions.set_generating(chat_id, False)
        sessions.set_progress(chat_id, None)

    if not resultado.ok:
        await _send_long(update, f"Falló: {resultado.mensaje}")
        return

    lineas = [f"*{resultado.titulo}*", resultado.mensaje, "", f"Carpeta: {resultado.carpeta_link}", ""]
    for t in resultado.trozos:
        lineas.append(f"{t.indice:02d}. {t.inicio_seg / 60:.0f}–{t.fin_seg / 60:.0f} min — {t.link}")
    await _send_long(update, "\n".join(lineas))


async def cmd_vacamorada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """UN video de crimen, de punta a punta, con Javier presentando desde la
    esquina y los labios sincronizados. Uso: /vacamorada [slug]

    Hace el flujo entero: le pide el guion a Claude, genera el video y le pone
    el presentador encima. Con un slug salta la escritura del guion y usa uno
    que ya existe -- sirve para reintentar sin gastar otra llamada a Claude.

    Es el modo caro: ~35 minutos extra por video sobre lo que ya tarda el
    pipeline normal. Por eso es un comando aparte y de a uno, no una opción
    del lote.

    A diferencia de /crimen + /generarlote, acá no hay pausa para revisar los
    hechos: el guion se muestra antes de arrancar, pero el comando sigue solo.
    """
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Ya hay algo corriendo desde {since}.")
        return

    # Las verificaciones ANTES de escribir el guion: descubrir después de
    # gastar una llamada a Claude que faltaba el modelo es el peor final
    # posible para este comando.
    falta = await asyncio.to_thread(pipeline.motor_tts_listo)
    if falta:
        await update.message.reply_text(f"⚠️ {falta}")
        return
    # Los argumentos pueden venir en cualquier orden y los dos son opcionales:
    # un número es el avatar, cualquier otra cosa es el slug de un guion ya
    # escrito. Así /vacamorada, /vacamorada 1 y /vacamorada 1 guion-x funcionan
    # sin que haya que recordar posiciones.
    avatar_num = None
    slug = None
    for arg in context.args or []:
        if arg.isdigit():
            avatar_num = int(arg)
        else:
            slug = arg

    falta = await asyncio.to_thread(avatar_presentador.disponible, avatar_num)
    if falta:
        await update.message.reply_text(f"⚠️ No puedo poner el presentador: {falta}")
        return
    if not slug:
        # Sin slug, el comando hace el flujo entero: escribe el guion y
        # genera. Con slug, reusa uno ya escrito -- sirve para reintentar sin
        # gastar otra llamada a Claude.
        await update.message.reply_text(
            f"🐄 Modo vaca morada, avatar {avatar_num or 0}. Primero le pido a Claude "
            f"un guion de crimen; eso tarda unos minutos."
        )
        session_id, is_new = _sesion_nueva()
        sessions.set_generating(chat_id, True)
        try:
            guiones = await _guiones_de_crimen(update, session_id, is_new, 1)
        except LimiteDeClaude as exc:
            await update.message.reply_text(
                "Se acabó la cuota de Claude, no pude escribir el guion. "
                + str(exc).replace("Error ejecutando Claude: ", ""))
            return
        finally:
            sessions.set_generating(chat_id, False)
        if not guiones:
            return
        guion = guiones[0]
        slug = guion.get("slug")
        if not slug:
            await update.message.reply_text("Claude devolvió un guion sin slug.")
            return
        # El guion se muestra ANTES de generar, aunque el comando no se
        # detenga: si los hechos están mal, mejor enterarse ahora y cortar con
        # /estatus que descubrirlo en el video publicado.
        await _send_long(
            update,
            f"📋 *{guion.get('titulo', slug)}*\n\n"
            f"{guion.get('resumen_hechos', '(sin resumen)')}\n\n"
            f"Arranco a generar. Si algún dato está mal, frená ahora.",
        )

    if not (ANDROID_IN / slug / "guion.json").exists():
        await update.message.reply_text(f"No tengo el guion.json de '{slug}'.")
        return

    voz = sessions.get_voice(chat_id)
    await update.message.reply_text(
        f"Generando '{slug}'. Sale el video de crimen normal y encima vas vos "
        f"presentando desde la esquina, con los labios sincronizados.\n\n"
        f"⏱️ Suma unos *35 minutos* a lo que tarda un video normal (el "
        f"sincronizado de labios corre en la Radeon). Cerrá los juegos: si la "
        f"GPU está ocupada, ese paso se queda sin memoria.\n\n"
        f"/estatus para ver el paso.",
        parse_mode=ParseMode.MARKDOWN,
    )

    sessions.set_generating(chat_id, True)
    try:
        result = await asyncio.to_thread(pipeline.run, slug, voz, chat_id, True, avatar_num)
    finally:
        sessions.set_generating(chat_id, False)
        sessions.set_progress(chat_id, None)

    # Se saca del lote pendiente igual que en /generarlote, para que no quede
    # dando vueltas y se regenere sin presentador en el próximo /generarlote.
    pendientes = sessions.get_pending_batch(chat_id)
    if slug in pendientes:
        sessions.set_pending_batch(chat_id, [s for s in pendientes if s != slug])

    if result.ok:
        await _send_long(update, f"🐄 Listo: {result.mensaje}")
        sessions.set_phase(chat_id, sessions.PHASE_IDLE)
        return

    if not result.necesita_claude:
        await _send_long(update, f"Falló: {result.mensaje}")
        return

    await _send_long(update, f"No pudo terminar solo:\n{result.mensaje}\n\nPaso esto a Claude...")
    await _dispatch_to_claude(update, INSTRUCCION_ESCALAR.format(slug=slug, detalle=result.mensaje))
    sessions.set_phase(chat_id, sessions.PHASE_IDLE)


class LimiteDeClaude(Exception):
    """Se acabó la cuota de Claude. No tiene sentido seguir pidiendo: cada
    intento falla en dos segundos hasta la hora que dice el mensaje."""


def _sesion_nueva() -> tuple[str, bool]:
    """Una conversación nueva con Claude, para trabajo que no necesita memoria.

    Escribir guiones no necesita el historial del chat: todo está en la
    instrucción y en disco. Y reusarlo es carísimo, porque Claude relee el
    historial ENTERO en cada paso. Medido el 26/09/2026: la sesión del chat
    llevaba desde el 19/08 (16 MB, ~900.000 tokens de contexto), y escribir 13
    guiones costó 34 millones de tokens y agotó la cuota a mitad del lote.
    """
    return str(uuid.uuid4()), True


def _sesion_recortada() -> bool:
    """BOT_SESION_RECORTADA (default 1): los guiones de crimen y mitos se
    escriben sin conectores MCP ni herramientas de más (13/10/2026: 39.9k ->
    24.4k tokens fijos por paso). Sigue en la carpeta del narrador porque la
    instrucción se apoya en su CLAUDE.md. 0 = como antes."""
    return (os.getenv("BOT_SESION_RECORTADA") or "1").strip() != "0"


def _ya_cubiertos(prefijo: str) -> str:
    """Títulos de lo que ya está hecho, para pegarlo en la instrucción.

    Antes la instrucción mandaba a Claude a abrir los guion.json de
    C:\\Android_in uno por uno para no repetir casos: cientos de archivos
    leídos en cada lote, y cada uno se queda en el contexto de todos los
    pasos que siguen. La lista cuesta unos pocos miles de tokens.
    """
    titulos = set()
    for ruta in sessions.ANDROID_IN.glob(f"{prefijo}*/guion.json"):
        try:
            titulo = json.loads(ruta.read_text(encoding="utf-8")).get("titulo")
        except (OSError, ValueError):
            continue
        if titulo:
            titulos.add(str(titulo).strip())
    return "; ".join(sorted(titulos)) or "(ninguno)"


async def _guiones_de_crimen(
    update: Update,
    session_id: str,
    is_new: bool,
    cantidad: int,
    desc: str = "de true crime",
    formato: str = CRIMEN,
) -> list[dict]:
    """Le pide a Claude `cantidad` guiones de crimen y devuelve los parseados.

    `formato` elige el ÁNGULO (ver formatos.py): las reglas de estructura,
    hechos y riesgo son siempre las mismas, lo que cambia es desde dónde se
    cuenta el caso -- y con eso, la apertura, que era idéntica en 67 de los
    69 guiones de crimen que había.

    Devuelve [] si Claude falló o si su respuesta no se pudo parsear, avisando
    por Telegram en ambos casos. Lo usan /crimen (dentro del lote) y
    /vacamorada (que escribe el suyo antes de generar).
    """
    if formato == formatos.MITO:
        # Instrucción propia y entera, no un párrafo sobre la de crimen: cambia
        # la persona, el sonido y las imágenes. Ver INSTRUCCION_MITO.
        instruccion = INSTRUCCION_MITO.format(n=cantidad)
    else:
        instruccion = INSTRUCCION_NUEVO_LOTE.format(n=cantidad)
        extra = formatos.instruccion_de(formato)
        if extra:
            # El párrafo de formato va AL FINAL: es lo último que lee el modelo y
            # manda sobre los ejemplos genéricos de la instrucción base.
            instruccion = f"{instruccion}\n\n{extra}"
    prefijo = "mito" if formato == formatos.MITO else "guion"
    instruccion += (
        "\n\nYA ESTÁN HECHOS -- no repitas ninguno, y usa ESTA lista en vez de abrir "
        "los guion.json uno por uno (abrirlos cuesta millones de tokens): "
        f"{_ya_cubiertos(prefijo)}"
    )
    result = await asyncio.to_thread(run_turn, session_id, instruccion, is_new, False, _sesion_recortada())
    if not result.ok:
        logger.error("Tramo %s falló: %s", desc, result.text[:2000])
        if es_limite_de_uso(result.text):
            raise LimiteDeClaude(result.text)
        await update.message.reply_text(f"Falló el tramo {desc}: {result.text}")
        return []
    guiones = _parse_lote_response(result.text)
    if not guiones:
        # Al log también: el texto que ve el usuario va cortado en trozos de
        # Telegram y no queda registro de qué contestó.
        logger.error(
            "Tramo %s sin lista de guiones parseable. Respuesta:\n%s",
            desc, result.text[:4000],
        )
        await update.message.reply_text(
            f"Claude terminó el tramo {desc} pero no pude parsear la lista de "
            "guiones de su respuesta. Esto es lo que contestó:"
        )
        await _send_long(update, result.text)
        return []
    if formato == formatos.MITO:
        _asegurar_formato_mito(g.get("slug") for g in guiones)
    else:
        guiones = await _revisar_guiones_crimen(update, session_id, guiones, desc)
    return guiones


def _problemas_de(slug: str, entrada: Path = sessions.ANDROID_IN) -> list[str]:
    try:
        guion = json.loads((entrada / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["no se pudo leer el guion.json"]
    return revision_guion.problemas(guion)


async def _revisar_guiones_crimen(update: Update, session_id: str, guiones: list[dict],
                                  desc: str) -> list[dict]:
    """Nombres, lugar exacto y evidencia: se comprueban, no se confían.

    Lo que falle vuelve a Claude UNA vez, en la misma sesión (ya tiene el caso
    investigado: corregir cuesta mucho menos que escribir de nuevo). Lo que
    siga fallando sale del lote: un true crime sin nombres suena a cuento, y
    uno sin evidencia saldría con imágenes de IA.
    """
    fallas = {g["slug"]: p for g in guiones if g.get("slug")
              if (p := _problemas_de(g["slug"]))}
    if not fallas:
        return guiones
    pedido = ("Revisé los guiones y estos no cumplen las reglas de NOMBRES, LUGAR EXACTO y "
              "EVIDENCIA REAL. Corrígelos en su guion.json (mismo slug). Si un caso no tiene "
              "la evidencia, reemplázalo por otro caso, con otro slug. Responde con el mismo "
              "bloque JSON de antes, con TODOS los guiones del tramo.\n\n"
              + "\n".join(f"- {slug}: " + "; ".join(p) for slug, p in fallas.items()))
    logger.info("Tramo %s: %d guion(es) a corregir", desc, len(fallas))
    result = await asyncio.to_thread(run_turn, session_id, pedido, False, False, _sesion_recortada())
    if result.ok:
        corregidos = _parse_lote_response(result.text)
        if corregidos:
            guiones = corregidos
    elif es_limite_de_uso(result.text):
        raise LimiteDeClaude(result.text)
    buenos, fuera = [], {}
    for g in guiones:
        p = _problemas_de(g.get("slug", ""))
        if p:
            fuera[g.get("slug", "?")] = p
        else:
            buenos.append(g)
    if fuera:
        await update.message.reply_text(
            f"⚠️ Tramo {desc}: {len(fuera)} guion(es) quedan FUERA del lote porque no "
            "cumplen nombres/lugar/evidencia ni después de corregirlos:\n"
            + "\n".join(f"- {s}: " + "; ".join(p) for s, p in fuera.items()))
    return buenos


def _asegurar_formato_mito(slugs, entrada: Path = sessions.ANDROID_IN) -> list[str]:
    """Pone `"formato": "mito"` en el guion.json si Claude lo olvidó.

    Es la marca que le dice al narrador que NO busque fotos de archivo. Sin
    ella, la búsqueda por nombres propios toma los nombres de todo el guion:
    en el POC del Yum Balam, por nombrar al Pombero de Paraguay, la
    advertencia en el monte de Yucatán se llenó de mapas de distritos de
    Paraguay y de un edificio de Avenida Paulista. Un olvido de una línea no
    puede costar eso, así que no depende de que Claude la escriba.

    Devuelve los slugs corregidos.
    """
    corregidos = []
    for slug in slugs:
        if not slug:
            continue
        ruta = entrada / slug / "guion.json"
        try:
            guion = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if guion.get("formato") != formatos.MITO:
            guion["formato"] = formatos.MITO
            ruta.write_text(json.dumps(guion, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
            corregidos.append(slug)
            logger.warning("Guion de mito sin 'formato': corregido en %s", slug)
    return corregidos


async def _pedir_lote(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reparto,
    cantidad: int | None = None,
    acumular: bool = False,
    sin_avatar: bool = False,
) -> None:
    """Le pide a la MISMA sesión de Claude de este chat que escriba varios
    guiones nuevos. No genera ningún video todavía -- eso es /generarlote,
    después de que el usuario revise la veracidad de estos.

    `reparto(n)` devuelve los tramos (instrucción, descripción, cantidad). Un
    lote mixto son dos tramos, uno por tipo: se le piden por separado porque
    cada uno tiene su propia plantilla y sus propias reglas de formato. Los
    slugs de todos los tramos terminan en el MISMO pending_batch, así que
    /generarlote los genera juntos como un solo lote.
    """
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    n = cantidad if cantidad is not None else _LOTE_DEFAULT
    if cantidad is None and context.args:
        try:
            n = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                f"Uso: {update.message.text.split()[0]} [cantidad] (default 5)"
            )
            return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Ya hay algo corriendo desde {since}.")
        return

    tramos = reparto(n)
    detalle = " + ".join(f"{cant} {desc}" for _, desc, cant in tramos)
    await update.message.reply_text(
        f"Armando {n} guiones nuevos ({detalle}). Las trivias salen del banco al "
        f"instante; los de crimen los escribe Claude y eso tarda."
    )

    sessions.set_generating(chat_id, True)
    todos: list[dict] = []
    faltan: list[tuple[str, str, int]] = []
    limite = ""
    try:
        for i, (tipo, desc, cant) in enumerate(tramos):
            # Conversación NUEVA por tramo, no la del chat: ver _sesion_nueva.
            session_id, is_new = _sesion_nueva()
            try:
                # Las trivias salen del banco de preguntas; Claude solo aparece
                # si faltan preguntas, y solo para proponerlas.
                if tipo == TRIVIA:
                    guiones, aviso = await asyncio.to_thread(
                        _generar_trivias, cant, session_id, is_new
                    )
                    if aviso:
                        await update.message.reply_text(aviso)
                    if len(guiones) < cant:
                        faltan.append((tipo, desc, cant - len(guiones)))
                    todos.extend(guiones)
                    continue

                # `continue` y no `break`: los otros tramos no dependen de este.
                if tipo.startswith(CERCANIA):
                    from dato_mata_gato_bot import fabrica
                    guiones, _ = await fabrica._guiones_de_cercania(update, tipo[len(CERCANIA):], cant)
                else:
                    guiones = await _guiones_de_crimen(update, session_id, is_new, cant,
                                                       desc, formato=tipo)
            except LimiteDeClaude as exc:
                # Acá sí se corta: con la cuota agotada cada intento falla en dos
                # segundos, y seguir solo llena el chat de errores. Lo que falta
                # se guarda para /completarlote.
                limite = str(exc)
                faltan.extend(tramos[i:])
                break
            if not guiones:
                faltan.append((tipo, desc, cant))
                continue
            for g in guiones:
                g["formato"] = tipo
            todos.extend(guiones)
    finally:
        sessions.set_generating(chat_id, False)
        sessions.set_tramos_faltantes(chat_id, faltan)

    if faltan:
        detalle_faltan = ", ".join(f"{c} {d}" for _, d, c in faltan)
        await update.message.reply_text(
            ("⚠️ Se acabó la cuota de Claude a mitad del lote.\n"
             f"{limite.replace('Error ejecutando Claude: ', '')}\n\n" if limite else
             "⚠️ Algunos tramos no salieron.\n\n")
            + f"Faltan: {detalle_faltan}.\n"
            "Cuando se libere, corre /completarlote y los agrego a este mismo lote."
        )

    if not todos:
        return

    slugs = [g["slug"] for g in todos if g.get("slug")]
    if acumular:
        slugs = sessions.get_pending_batch(chat_id) + slugs
    else:
        # Un lote nuevo reemplaza al anterior, y con él su marca: si no, un
        # /lotegrande después de un /lotefish3 saldría sin presentadores.
        sessions.set_lote_sin_avatar(chat_id, sin_avatar)
    sessions.set_pending_batch(chat_id, slugs)

    lineas = [f"Generó {len(todos)} guion(es) nuevo(s) -- revisá la veracidad antes de generar los videos:\n"]
    for g in todos:
        lineas.append(f"• {g.get('titulo', g.get('slug'))}\n  {g.get('resumen_hechos', '(sin resumen)')}")
    if acumular:
        lineas.append(f"El lote ahora tiene {len(slugs)} guiones en total.")
    lineas.append("\nCuando lo hayas revisado, corré /generarlote (o /generargrande).")
    await _send_long(update, "\n\n".join(lineas))


async def _enviar_hoja_de_contacto(update: Update, slug: str) -> None:
    """Si el video es un mito, manda la hoja con todas sus imágenes para
    revisarlas antes de publicar (ver pipeline.hoja_de_contacto). Nunca tira:
    en un lote de horas, una foto que no llega no puede cortar el resto."""
    try:
        hoja = await asyncio.to_thread(pipeline.hoja_de_contacto, slug)
        if hoja is None:
            return
        with open(hoja, "rb") as f:
            await update.message.reply_photo(
                f, caption=f"Imágenes de '{slug}': revísalas antes de publicar. "
                           "Si alguna muestra un cuerpo desnudo, una cara rara o un niño, "
                           "no lo publiques y avísame qué toma es.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo mandar la hoja de contacto de %s: %s", slug, exc)


async def _safe_reply(update: Update, text: str) -> None:
    """reply_text que nunca tira -- un hipo de red de Telegram (visto real:
    httpx.ReadTimeout/Bad Gateway al avisar progreso) no debe matar todo
    /generarlote a mitad de camino. Sin esto, un aviso fallido silenciaba el
    resto del lote entero (confirmado: se generaron 2/5 videos bien, pero
    el crash al avisar el 2º dejó los otros 3 sin ni siquiera intentarse)."""
    try:
        await update.message.reply_text(text)
    except Exception as exc:  # noqa: BLE001 — un aviso es best-effort, no crítico
        logger.warning("No pude mandar un mensaje de progreso (%s): %s", exc, text[:200])


async def cmd_generarlote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Corre /generar en cadena para cada guion del último lote, uno
    detrás del otro (no en paralelo -- A1111/GPU es compartido). Si un
    video escala a Claude, no bloquea el lote: sigue con el siguiente y lo
    reporta al final. Cada slug se saca de pending_batch apenas termina
    (no todos juntos al final) -- así el lote es resumible: si el proceso
    se cae por lo que sea, correr /generarlote de nuevo retoma justo en lo
    que falta, sin repetir lo ya generado."""
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slugs = sessions.get_pending_batch(chat_id)
    if not slugs:
        await update.message.reply_text("No hay ningún lote pendiente -- usá /crimen o /trivia primero.")
        return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Ya hay algo corriendo desde {since}.")
        return

    # Antes de arrancar, no a los dos minutos: sin el contenedor arriba el
    # primer video se cae en el audio y escala a Claude -- quince minutos y una
    # llamada para algo que se pregunta en dos segundos.
    falta = await asyncio.to_thread(pipeline.motor_tts_listo)
    if falta:
        await update.message.reply_text(f"⚠️ {falta}\n\nEl lote queda pendiente: volvé a "
                                        "mandar /generarlote cuando esté listo.")
        return

    voz = sessions.get_voice(chat_id)
    total = len(slugs)
    await _safe_reply(
        update,
        f"Arrancando el lote de {total} video(s), uno detrás del otro. "
        f"/estatus para ver en cuál va.",
    )

    ok_list: list[str] = []
    escalados: list[str] = []
    fallidos: list[str] = []
    restantes = list(slugs)
    for i, slug in enumerate(slugs, start=1):
        await _safe_reply(update, f"({i}/{total}) Generando '{slug}'...")
        try:
            sessions.set_generating(chat_id, True)
            try:
                result = await asyncio.to_thread(pipeline.run, slug, voz, chat_id)
            finally:
                sessions.set_generating(chat_id, False)
                sessions.set_progress(chat_id, None)

            if result.ok:
                ok_list.append(slug)
                await _safe_reply(update, f"({i}/{total}) '{slug}' listo: {result.mensaje}")
                await _enviar_hoja_de_contacto(update, slug)
            elif result.necesita_claude:
                escalados.append(slug)
                await _safe_reply(
                    update,
                    f"({i}/{total}) '{slug}' quedó sin terminar solo -- paso a Claude:\n{result.mensaje}",
                )
                await _dispatch_to_claude(update, INSTRUCCION_ESCALAR.format(slug=slug, detalle=result.mensaje))
            else:
                fallidos.append(slug)
                await _safe_reply(update, f"({i}/{total}) '{slug}' falló: {result.mensaje}")
        except Exception as exc:  # noqa: BLE001 — un slug roto no debe tirar el resto del lote
            fallidos.append(slug)
            logger.error("cmd_generarlote: '%s' explotó de forma inesperada: %s", slug, exc)
            await _safe_reply(update, f"({i}/{total}) '{slug}' explotó de forma inesperada: {exc}")
        finally:
            restantes.remove(slug)
            sessions.set_pending_batch(chat_id, restantes)

    sessions.set_phase(chat_id, sessions.PHASE_IDLE)
    await _safe_reply(
        update,
        f"Lote terminado. OK sin Claude: {len(ok_list)}. Escalados a Claude: {len(escalados)}. "
        f"Fallidos: {len(fallidos)}.",
    )


async def cmd_generargrande(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Genera el lote pendiente en modo lote grande: archiva sin publicar.

    Aparte de /generarlote porque las dos diferencias importan y no conviene
    que dependan de recordar una bandera: acá NADA se sube a Drive ni entra al
    calendario, y uno de cada diez videos lleva presentador rotando entre los
    tres avatares. Ver lote_grande.py.
    """
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slugs = sessions.get_pending_batch(chat_id)
    if not slugs:
        await update.message.reply_text("No hay lote pendiente -- usá /lotegrande primero.")
        return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Ya hay algo corriendo desde {since}.")
        return

    # Las dos verificaciones caras ANTES de arrancar: descubrir a la tercera
    # hora que faltaba el motor de voz sería el peor final posible para esto.
    falta = await asyncio.to_thread(pipeline.motor_tts_listo)
    if falta:
        await update.message.reply_text(f"⚠️ {falta}\n\nEl lote queda pendiente.")
        return
    sin_avatar = sessions.get_lote_sin_avatar(chat_id)
    falta = "" if sin_avatar else await asyncio.to_thread(avatar_presentador.disponible)
    if falta:
        await update.message.reply_text(f"⚠️ No puedo poner presentadores: {falta}")
        return

    plan = lote_grande.planificar(list(slugs),
                                  con_avatar=not sessions.get_lote_sin_avatar(chat_id))
    lote_grande.repartir_voces(plan)  # prueba Fish 3 / voz de Javier (11/10/2026)
    await _safe_reply(
        update,
        f"🎬 Lote grande\n{plan.resumen()}\n\n"
        f"No se sube nada a Drive. Cerrá los juegos: los videos con presentador "
        f"necesitan la GPU libre.\n/estatus para ver en cuál va.",
    )

    ok_list: list[str] = []
    fallidos: list[str] = []
    restantes = list(slugs)
    total = len(plan.tareas)
    for i, (slug, avatar_num) in enumerate(plan.tareas, start=1):
        # El corte de la pausa va ACÁ, entre videos: A1111 se baja con un
        # video terminado y no a mitad de una imagen. Ver cmd_pausa.
        if sessions.get_pausa(chat_id):
            bajo = await asyncio.to_thread(pipeline._detener_a1111)
            await _safe_reply(
                update,
                f"⏸️ Lote pausado antes de ({i}/{total}). "
                + ("A1111 cerrado, la gráfica queda libre. " if bajo else "")
                + "Quedan "
                f"{len(restantes)} por generar.\n/reanudar cuando quieras seguir.",
            )
            while sessions.get_pausa(chat_id):
                await asyncio.sleep(5)
            await _safe_reply(update, f"▶️ Sigo el lote en ({i}/{total}).")

        etq = f"({i}/{total}) '{slug}'" + (f" con avatar {avatar_num}" if avatar_num is not None else "")
        await _safe_reply(update, f"{etq}...")
        try:
            sessions.set_generating(chat_id, True)
            try:
                result = await asyncio.to_thread(
                    pipeline.run, slug, sessions.get_voice(chat_id), chat_id,
                    avatar_num is not None, avatar_num, plan.carpeta,
                )
            finally:
                sessions.set_generating(chat_id, False)
                sessions.set_progress(chat_id, None)
            if result.ok:
                ok_list.append(slug)
                await _safe_reply(update, f"{etq} listo: {result.mensaje}")
                await _enviar_hoja_de_contacto(update, slug)
            else:
                # En un lote de once horas, un guion roto NO puede cortar el
                # resto ni disparar una corrida de Claude por cada fallo: se
                # anota y se sigue.
                fallidos.append(slug)
                logger.error("lote grande: '%s' falló: %s", slug, result.mensaje)
                await _safe_reply(update, f"{etq} falló: {result.mensaje[:400]}")
        except Exception as exc:  # noqa: BLE001 -- un slug roto no tira el lote
            fallidos.append(slug)
            logger.error("lote grande: '%s' explotó: %s", slug, exc)
            await _safe_reply(update, f"{etq} explotó: {exc}")
        finally:
            # Con `/pausa ya` el video se cortó a propósito: NO se saca de la
            # cola, porque hay que rehacerlo. El bucle termina y se retoma
            # con /generargrande, que rearma el plan con lo que quedó.
            if not sessions.get_pausa(chat_id):
                restantes.remove(slug)
                sessions.set_pending_batch(chat_id, restantes)

        if sessions.get_pausa(chat_id) and slug in restantes:
            await _safe_reply(
                update,
                f"⏸️ Lote cortado en ({i}/{total}). '{slug}' vuelve a la cola.\n"
                f"Quedan {len(restantes)}. Retomá con /generargrande.",
            )
            break

    sessions.set_phase(chat_id, sessions.PHASE_IDLE)
    # Texto plano a propósito: _send_long parte el mensaje en trozos y no usa
    # parse_mode, así que cualquier marca de Markdown se vería literal.
    lineas = [
        "🎬 LOTE GRANDE TERMINADO",
        f"Listos: {len(ok_list)}   Fallidos: {len(fallidos)}",
        "",
        f"📁 Carpeta: {plan.carpeta.name}",
        "Ruta completa:",
        str(plan.carpeta),
        "",
        "⚠️ NO se subió nada a Drive ni entró al calendario de publicación: "
        "son para revisar y publicar a mano.",
    ]
    archivos = sorted(plan.carpeta.glob("*.mp4")) if plan.carpeta.exists() else []
    if archivos:
        lineas += ["", f"Los {len(archivos)} videos:"]
        lineas += [f"  {a.name}  ({a.stat().st_size / 1e6:.0f} MB)" for a in archivos]
    if fallidos:
        lineas += ["", "Sin generar:"] + [f"  {s}" for s in fallidos]
    await _send_long(update, "\n".join(lineas))


async def cmd_publicarfacebook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publica un video YA GENERADO en la Página de Facebook configurada --
    manual a propósito, nunca se dispara solo desde /generar ni /generarlote
    todavía (a pedido explícito: primero probarlo, engancharlo después)."""
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = context.args[0] if context.args else sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text("Uso: /publicarfacebook <slug> (o corré /nuevovideo antes para fijar uno)")
        return

    final_mp4 = pipeline.NARRATOR_PROJECTS / slug / "final.mp4"
    if not final_mp4.exists():
        await update.message.reply_text(f"No existe {final_mp4} -- generá el video primero con /generar.")
        return

    await update.message.reply_text(f"Publicando '{slug}' en Facebook...")
    ok, salida = await asyncio.to_thread(pipeline.publish_to_facebook, slug)
    if ok:
        await update.message.reply_text(f"Publicado en Facebook.\n{salida}")
    else:
        await update.message.reply_text(f"Falló:\n{salida}")


async def cmd_publicartiktok(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publica un video YA GENERADO en TikTok -- manual a propósito, igual
    que /publicarfacebook. Sin auditoría de TikTok, queda en modo privado
    (SELF_ONLY): solo lo ve la cuenta que autorizó la app."""
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = context.args[0] if context.args else sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text("Uso: /publicartiktok <slug> (o corré /nuevovideo antes para fijar uno)")
        return

    final_mp4 = pipeline.NARRATOR_PROJECTS / slug / "final.mp4"
    if not final_mp4.exists():
        await update.message.reply_text(f"No existe {final_mp4} -- generá el video primero con /generar.")
        return

    await update.message.reply_text(
        f"Publicando '{slug}' en TikTok (modo privado hasta que la app esté auditada)..."
    )
    ok, salida = await asyncio.to_thread(pipeline.publish_to_tiktok, slug)
    if ok:
        await update.message.reply_text(f"Publicado en TikTok.\n{salida}")
    else:
        await update.message.reply_text(f"Falló:\n{salida}")


async def cmd_investigar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Herramienta de investigación manual, aparte del pipeline: busca
    imágenes de contenido con licencia libre a partir de una URL de
    Wikipedia, un plano del proyecto actual, o palabras clave sueltas --
    y las manda para que el usuario elija cuál usar. Si falla, no afecta
    a /generar ni a nada más del bot -- solo avisa."""
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "Uso:\n"
            "/investigar <url de Wikipedia>\n"
            "/investigar <id de plano, ej. p02> — arma la búsqueda solo con el "
            "título del guion + nombres propios de la narración de ese plano\n"
            "/investigar <palabras clave sueltas>\n\n"
            "Busca en Wikipedia + Openverse + NASA (todas con licencia verificada). "
            "Para usar una imagen en un plano, reenviámela con el texto p1 [inicio] [1]."
        )
        return

    arg = " ".join(context.args)
    es_url = arg.startswith("http")

    if es_url:
        buscar_por_query = False
        query_o_url = arg
    else:
        slug = sessions.get_slug(chat_id)
        plano = summary.find_plano(summary.load_guion_dict(slug), arg) if slug else None
        if plano is not None:
            guion = summary.load_guion_dict(slug)
            query_o_url = auto_query.build_query(guion.get("titulo", ""), plano.get("narracion", ""))
            if not query_o_url:
                await update.message.reply_text(
                    f"No pude sacar palabras clave del plano '{arg}' (narración vacía o "
                    f"sin nombres propios) — probá con /investigar <palabras clave>."
                )
                return
            await update.message.reply_text(f"Plano {arg} → busco: \"{query_o_url}\"")
        else:
            query_o_url = arg
        buscar_por_query = True

    await update.message.reply_text("Buscando imágenes con licencia libre...")

    try:
        if buscar_por_query:
            imagenes = await asyncio.to_thread(free_image_search.search_all, query_o_url)
        else:
            imagenes = await asyncio.to_thread(free_image_search.search_wikipedia_url, query_o_url)
    except Exception as exc:
        logger.warning("investigar falló para %r: %s", query_o_url, exc)
        await update.message.reply_text(
            f"No pude investigar eso ({exc}). No afecta al resto del bot — /generar sigue normal."
        )
        return

    if not imagenes:
        await update.message.reply_text("No encontré imágenes con licencia libre para eso.")
        return

    await update.message.reply_text(f"Encontré {len(imagenes)} imagen(es):")
    for img in imagenes:
        caption = f"{img.titulo}\nFuente: {img.fuente}\nLicencia: {img.licencia or '(sin dato)'}\nAutor: {img.autor or '(sin dato)'}"
        try:
            await update.message.reply_photo(photo=img.url, caption=caption[:1024])
        except Exception as exc:
            logger.warning("No pude mandar %s: %s", img.url, exc)
            await update.message.reply_text(f"No pude mandar {img.titulo} ({exc}).")


# Tope de archivos que se reenvían por Telegram como preview -- el resto
# queda igual en disco, solo se evita floodear el chat.
_SCRAPE_PREVIEW_MAX = 8


async def cmd_scrapear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """POC suelto (ver scrape_poc.py): baja imágenes/audio de UNA página
    (no recorre el resto del sitio todavía) y manda una vista previa por
    Telegram. Sin relación con el pipeline -- si esto falla no afecta a
    /generar ni a nada más."""
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    if not context.args or not context.args[0].startswith("http"):
        await update.message.reply_text(
            "Uso: /scrapear <url>\n"
            "Baja las imágenes y audios de esa página (solo esa, no recorre el resto del sitio) "
            "y te manda una vista previa acá."
        )
        return

    url = context.args[0]
    out_dir = sessions.DATA_DIR / "scrape_poc" / _slugify(urlparse(url).netloc + urlparse(url).path)
    await update.message.reply_text(f"Cargando {url}...")
    try:
        imagenes, audios = await asyncio.to_thread(scrape_poc.scrape_page, url, out_dir)
    except Exception as exc:
        await update.message.reply_text(f"Falló: {exc}")
        return

    await update.message.reply_text(
        f"Encontré {len(imagenes)} imagen(es) y {len(audios)} audio(s). Guardado en {out_dir}"
    )
    for img in imagenes[:_SCRAPE_PREVIEW_MAX]:
        try:
            await update.message.reply_photo(photo=img.open("rb"))
        except Exception as exc:
            logger.warning("No pude mandar %s: %s", img, exc)
    for aud in audios[:_SCRAPE_PREVIEW_MAX]:
        try:
            await update.message.reply_audio(audio=aud.open("rb"))
        except Exception as exc:
            logger.warning("No pude mandar %s: %s", aud, exc)


async def cmd_videos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update.effective_chat.id):
        await _reject_unauthorized(update)
        return
    videos = generated_videos.list_generated_videos()
    await _send_long(update, generated_videos.format_video_list(videos))


async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text("No sé de qué proyecto — usa /nuevovideo primero.")
        return

    texto = summary.build_summary(slug)
    await _send_long(update, texto)


async def cmd_voz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    if not context.args:
        actual = sessions.get_voice(chat_id)
        await update.message.reply_text(
            f"Voz actual: {actual}\nDisponibles: {', '.join(VOICES)}\n"
            f"Para cambiarla: /voz <nombre>"
        )
        return

    voz = context.args[0].strip().lower()
    if voz not in VOICES:
        await update.message.reply_text(
            f"No conozco esa voz. Disponibles: {', '.join(VOICES)}"
        )
        return

    sessions.set_voice(chat_id, voz)
    await update.message.reply_text(f"Listo, voz para el próximo /generar: {voz}")


async def cmd_logo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    actual = sessions.logo_path()
    sessions.set_awaiting_logo(chat_id, True)
    aviso_actual = f" (ya hay uno: {actual.name})" if actual else ""
    await update.message.reply_text(
        f"Mándame la imagen del logo del canal{aviso_actual} — se va a usar siempre "
        f"en el plano 0 de todos los videos nuevos."
    )


async def cmd_cierre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    actual = sessions.cierre_path()
    sessions.set_awaiting_cierre(chat_id, True)
    aviso_actual = f" (ya hay uno: {actual.name})" if actual else ""
    await update.message.reply_text(
        f"Mándame la imagen de cierre del canal{aviso_actual} — se va a usar siempre "
        f"en el plano final de todos los videos nuevos."
    )


async def cmd_pausa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pausa el lote para devolverle la gráfica al usuario. Uso: /pausa [ya]

    Sin argumento, la pausa entra en el corte ENTRE videos: el que está
    corriendo se termina (unos quince minutos) y recién ahí se baja A1111 y
    el lote se queda esperando /reanudar. No se pierde nada.

    Con `ya`, se corta el video en curso. Ese video vuelve a la cola y el
    bucle termina: hay que retomar con /generargrande, que rearma el plan con
    lo que quedó pendiente. Es más brusco, pero libera la placa en segundos.

    Por qué existe: A1111 se queda con ~2.8 GB de los 8 de la placa esté
    generando o no, y suspender el proceso NO devuelve esa memoria (medido el
    23/09/2026 con Gears 5 abierto: 7.9 GB de 8 ocupados, el juego sin aire).
    Para jugar hay que cerrar A1111 de verdad, y eso obliga a cortar el lote
    en un punto limpio en vez de a mitad de una imagen.
    """
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    ya = bool(context.args) and context.args[0].lower() in ("ya", "ahora")
    sessions.set_pausa(chat_id, True)

    if not ya:
        corriendo, _ = sessions.get_generating(chat_id)
        await update.message.reply_text(
            "⏸️ Pausa pedida.\n"
            + ("Termino el video que está corriendo y ahí paro (puede tardar "
               "unos quince minutos). " if corriendo else "")
            + "Cuando pare bajo A1111 y te queda la gráfica libre.\n\n"
            "Si lo necesitás ahora mismo: /pausa ya (se pierde el video en curso).\n"
            "Para seguir: /reanudar"
        )
        return

    cortado = await asyncio.to_thread(pipeline.detener_generacion)
    bajo = await asyncio.to_thread(pipeline._detener_a1111)
    await update.message.reply_text(
        "⏸️ Cortado.\n"
        f"{'Se cortó el video en curso; vuelve a la cola.' if cortado else 'No había video corriendo.'}\n"
        f"{'A1111 cerrado: la gráfica queda libre.' if bajo else 'A1111 no estaba arriba.'}\n\n"
        "Para seguir: /generargrande (retoma con los que quedaron pendientes)."
    )


async def cmd_reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Saca la pausa. Si el lote seguía vivo esperando, sigue solo."""
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return
    if not sessions.get_pausa(chat_id):
        await update.message.reply_text("No hay ninguna pausa puesta.")
        return
    sessions.set_pausa(chat_id, False)
    pendientes = sessions.get_pending_batch(chat_id)
    corriendo, _ = sessions.get_generating(chat_id)
    if corriendo:
        await update.message.reply_text("▶️ Listo, sigo con el lote.")
    else:
        await update.message.reply_text(
            "▶️ Pausa quitada.\n"
            + (f"Quedan {len(pendientes)} guiones pendientes: corré /generargrande."
               if pendientes else "No hay lote pendiente.")
        )


async def cmd_estatus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = sessions.get_slug(chat_id) or "(ninguno)"
    running, since = sessions.get_generating(chat_id)
    if not running:
        await update.message.reply_text(f"Nada corriendo ahora. Proyecto actual: {slug}")
        return

    started = datetime.fromisoformat(since)
    elapsed_min = int((datetime.now(timezone.utc) - started).total_seconds() // 60)
    paso = sessions.get_progress(chat_id) or "arrancando"
    await update.message.reply_text(
        f"Generando '{slug}' desde hace {elapsed_min} min.\nPaso actual: {paso}"
    )


async def cmd_nuevo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return
    sessions.reset_session(chat_id)
    await update.message.reply_text("Conversación con Claude reiniciada.")


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    doc = update.message.document
    suffix = Path(doc.file_name or "").suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        tg_file = await doc.get_file()
        await _handle_image(update, chat_id, tg_file, suffix)
        return

    if suffix != ".json":
        await update.message.reply_text(
            f"Recibí un archivo ({doc.file_name}) que no reconozco — esperaba "
            f".json (guion) o una imagen ({', '.join(sorted(IMAGE_EXTENSIONS))})."
        )
        return

    slug = sessions.get_slug(chat_id)
    if not slug:
        caption = (update.message.caption or "").strip()
        slug = _slugify(caption or Path(doc.file_name).stem)

    dest_dir = ANDROID_IN / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "guion.json"

    tg_file = await doc.get_file()
    await tg_file.download_to_drive(custom_path=str(dest_path))

    sessions.set_slug(chat_id, slug)
    await update.message.reply_text(
        f"Guion recibido para '{slug}'. Mándame imágenes si quieres "
        f"(p1 [inicio] [1]), o escribe /generar cuando estés listo."
    )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return
    photo = update.message.photo[-1]  # la de mayor resolución
    tg_file = await photo.get_file()
    await _handle_image(update, chat_id, tg_file, ".jpg")


async def _handle_image(update: Update, chat_id: int, tg_file, suffix: str) -> None:
    """Guarda la imagen directo en Android_in/<slug>/imagenes_manuales/ —
    NO invoca a Claude. Eso pasa recien con /generar."""
    if sessions.is_awaiting_logo(chat_id):
        sessions.LOGO_DIR.mkdir(parents=True, exist_ok=True)
        # Borra cualquier logo anterior con otra extension antes de guardar
        # el nuevo, para que sessions.logo_path() no encuentre dos.
        for old in sessions.LOGO_DIR.glob(f"{sessions.LOGO_STEM}.*"):
            old.unlink()
        dest_path = sessions.LOGO_DIR / f"{sessions.LOGO_STEM}{suffix}"
        await tg_file.download_to_drive(custom_path=str(dest_path))
        sessions.set_awaiting_logo(chat_id, False)
        await update.message.reply_text(
            f"Logo guardado en {dest_path}. Se va a usar en el plano 0 de ahora en adelante."
        )
        return

    if sessions.is_awaiting_cierre(chat_id):
        sessions.LOGO_DIR.mkdir(parents=True, exist_ok=True)
        for old in sessions.LOGO_DIR.glob(f"{sessions.CIERRE_STEM}.*"):
            old.unlink()
        dest_path = sessions.LOGO_DIR / f"{sessions.CIERRE_STEM}{suffix}"
        await tg_file.download_to_drive(custom_path=str(dest_path))
        sessions.set_awaiting_cierre(chat_id, False)
        await update.message.reply_text(
            f"Cierre guardado en {dest_path}. Se va a usar en el plano final de ahora en adelante."
        )
        return

    slug = sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text(
            "Todavía no sé de qué proyecto es esta imagen — usa /nuevovideo y "
            "mándame el guion.json primero."
        )
        return

    caption = (update.message.caption or "").strip()
    spec = image_naming.parse(caption)
    if spec is None:
        await update.message.reply_text(
            "No reconocí el formato del texto de esta imagen. Mándala de nuevo "
            "con un texto así: p1 [inicio] [1]  (número de plano, posición, índice)."
        )
        return

    dest_dir = sessions.manual_images_dir_for(slug)
    dest_path = dest_dir / image_naming.filename_for(spec, suffix)
    await tg_file.download_to_drive(custom_path=str(dest_path))

    await update.message.reply_text(
        f"Guardada: plano {spec.plano_id}, posición {spec.posicion}, toma {spec.indice}. "
        f"({dest_path})"
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Sigo trabajando en la generación (desde {since}).")
        return

    await _dispatch_to_claude(update, update.message.text)


async def job_publicacion_diaria(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publica en Facebook el video que toca hoy y avisa por Telegram.
    Corre 20:00 hora de México (ver HORA_PUBLICACION). Es idempotente: si el
    video de hoy ya se publicó, no hace nada -- el bot se relanza solo al
    iniciar sesión de Windows y el job podría dispararse de nuevo el mismo
    día. TikTok NO se automatiza (audit pendiente), solo se manda el
    material listo para subirlo a mano."""
    hoy = datetime.now(ZoneInfo(daily_publish.TIMEZONE)).date()
    video = daily_publish.video_del_dia(hoy)
    if video is None:
        logger.info("Publicación diaria: nada agendado para %s", hoy)
        return

    # publicar_en_facebook hace I/O de red y subprocess: fuera del loop.
    ok, texto = await asyncio.to_thread(daily_publish.publicar_en_facebook, video)
    logger.info("Publicación diaria de %s: ok=%s", video.slug, ok)

    if ok:
        texto = f"{texto}\n\n{daily_publish.mensaje_tiktok(video)}"

    for chat_id in ALLOWED_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=texto, parse_mode=ParseMode.MARKDOWN
            )
        except Exception:  # noqa: BLE001 -- un chat caído no debe romper el resto
            logger.exception("No se pudo avisar la publicación a %s", chat_id)


def main() -> None:
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el .env")

    if not ALLOWED_CHAT_IDS:
        logger.warning(
            "TELEGRAM_ALLOWED_CHAT_IDS está vacío: nadie puede usar el bot todavía "
            "(seguro por defecto). Escríbele al bot para que te diga tu chat_id."
        )

    # Si el proceso anterior murió a mitad de una generación, su bandera quedó
    # encendida en disco y el bot no volvería a arrancar nada. Ver
    # sessions.limpiar_generaciones_colgadas().
    colgados = sessions.limpiar_generaciones_colgadas()
    if colgados:
        logger.warning(
            "Había %d chat(s) marcados como 'generando' de una corrida anterior "
            "que no terminó; bandera apagada: %s", len(colgados), ", ".join(colgados)
        )

    async def _post_init(app: Application) -> None:
        await app.bot.set_my_commands(BOT_COMMANDS)

    app = Application.builder().token(token).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["ayuda", "help"], cmd_ayuda))
    app.add_handler(CommandHandler("nuevovideo", cmd_nuevovideo))
    app.add_handler(CommandHandler("generar", cmd_generar))
    app.add_handler(CommandHandler("estatus", cmd_estatus))
    app.add_handler(CommandHandler("resumen", cmd_resumen))
    app.add_handler(CommandHandler("videos", cmd_videos))
    app.add_handler(CommandHandler("investigar", cmd_investigar))
    app.add_handler(CommandHandler("scrapear", cmd_scrapear))
    app.add_handler(CommandHandler("lote", cmd_lote))
    app.add_handler(CommandHandler("shorts", cmd_shorts))
    app.add_handler(CommandHandler("vacamorada", cmd_vacamorada))
    app.add_handler(CommandHandler("crimen", cmd_crimen))
    app.add_handler(CommandHandler("trivia", cmd_trivia))
    app.add_handler(CommandHandler("lotefish3", cmd_lotefish3))
    app.add_handler(CommandHandler("mitos", cmd_mitos))
    app.add_handler(CommandHandler("completarlote", cmd_completarlote))
    # Alias del nombre viejo: sigue apuntando al lote de true crime para no
    # romper la costumbre de quien ya lo usaba.
    app.add_handler(CommandHandler("nuevolote", cmd_crimen))
    app.add_handler(CommandHandler("generarlote", cmd_generarlote))
    app.add_handler(CommandHandler("lotegrande", cmd_lotegrande))
    app.add_handler(CommandHandler("generargrande", cmd_generargrande))
    app.add_handler(CommandHandler("pausa", cmd_pausa))
    app.add_handler(CommandHandler("reanudar", cmd_reanudar))
    app.add_handler(CommandHandler("publicarfacebook", cmd_publicarfacebook))
    app.add_handler(CommandHandler("publicartiktok", cmd_publicartiktok))
    app.add_handler(CommandHandler("voz", cmd_voz))
    app.add_handler(CommandHandler("logo", cmd_logo))
    app.add_handler(CommandHandler("cierre", cmd_cierre))
    app.add_handler(CommandHandler("nuevo", cmd_nuevo))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    if PUBLICACION_AUTOMATICA:
        app.job_queue.run_daily(
            job_publicacion_diaria,
            time=HORA_PUBLICACION,
            name="publicacion_diaria",
        )
        logger.info(
            "Publicación diaria agendada a las %s (%s)",
            HORA_PUBLICACION.strftime("%H:%M"),
            daily_publish.TIMEZONE,
        )
    else:
        logger.info(
            "Publicación automática APAGADA (PUBLICACION_AUTOMATICA=1 para prenderla); "
            "las publicaciones las hace el usuario a mano"
        )

    logger.info("Bot arrancado, escuchando Telegram (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
