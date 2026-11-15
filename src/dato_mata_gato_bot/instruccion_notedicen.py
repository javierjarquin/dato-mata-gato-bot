"""Fórmula de LO QUE NO TE DICEN (06/11/2026): un cobro, una regla, un derecho o
una letra chiquita que le toca a casi todos y que casi nadie conoce.

Sale de la prueba de un mes con todos los formatos juntos
(clip_assistance/analisis/prueba_formatos_mes.md). El pilar 7 de la fórmula de
cercanía, valor práctico, pasa de ser una pieza a ser el tema: es lo que la
gente guarda y comparte, porque le sirve. Perenne: la regla no se vence en
tres días.

Lo que la separa de un "tip" de internet es que la regla sale de un papel
vigente (ley, artículo, NOM, reglamento, la autoridad que la vigila) y que el
video dice qué hacer, paso a paso, sin prometer el resultado.
"""

import re

INSTRUCCION = r"""
Vas a escribir <<N>> guiones de video corto (45 a 75 segundos) para el canal Dato Mata Gato.

EL TEMA
<<TEMA>>

DE QUÉ VA ESTA FÓRMULA: "LO QUE NO TE DICEN"
Un cobro, una regla, un derecho o una letra chiquita que le toca a casi cualquiera en México
y que casi nadie conoce, o que alguien prefiere que no conozcas. Ejemplos del tipo de tema
(no los copies, busca el tuyo): la comisión que el banco no puede cobrarte, la propina que
no es obligatoria, lo que te tienen que devolver si cancelan tu vuelo, el aguinaldo que te
toca aunque renuncies, el cobro de reconexión de la luz, la garantía que la tienda dice que
no existe, la multa que no procede, lo que pasa con tu Afore si nunca la reclamas.
Lo que mueve el video es el choque entre LO QUE TE DICEN (el cajero, el contrato, la
costumbre, "así es la política de la empresa") y LO QUE DICE LA REGLA.
La gente comenta su caso ("a mí me lo cobraron") y lo guarda para cuando le pase.

LOS CANDADOS (sin uno de ellos no hay video; cámbiate de tema)
1. LA REGLA TIENE PAPEL Y ESTÁ VIGENTE. Sale de una ley con su artículo, una NOM, un
   reglamento, una disposición de la autoridad (PROFECO, CONDUSEF, Banxico, la autoridad de
   telecomunicaciones, CFE, IMSS, Infonavit, CONSAR, SAT, STPS, la Agencia Federal de Aviación
   Civil). Abres la fuente y confirmas que sigue vigente (fecha
   de la última reforma o de la publicación). Un blog o un video de otra cuenta NO es la
   regla: es una pista para buscarla.
2. SE PUEDE HACER. Quien ve sale sabiendo QUÉ HACER: a dónde va o a qué número llama, qué
   pide y cómo, qué lleva, cuánto cuesta y en qué plazo. Mínimo dos pasos concretos, con la
   fuente de cada uno.
3. SIN PROMETER EL RESULTADO. "Tienes derecho a pedirlo", "la regla dice", "puedes
   reclamarlo ante…"; nunca "te lo van a devolver" ni "gana seguro". No es asesoría
   personal: si el caso depende de algo (tu contrato, tu estado, tu tipo de cuenta), se
   dice de qué depende.
4. LAS EMPRESAS CON DATO, NO CON ADJETIVO. Si nombras una empresa, es con un dato público
   (las quejas en el Buró Comercial de PROFECO o en el SIPRES y el Buró de Entidades
   Financieras de CONDUSEF, una sanción publicada, una resolución). Nada de "te roban" ni
   "es un fraude" sin resolución que lo diga.
5. EL NÚMERO. Cuánta gente le pasa o cuánto dinero es: quejas, montos recuperados,
   comisiones cobradas, cuentas sin reclamar. Con su fuente y su año. Si no hay cifra
   oficial, no la inventes: di que no hay.

LAS PIEZAS DE LA FÓRMULA DE CERCANÍA SIGUEN (en "_schema.condiciones")
1_te_afecta (a quién le toca: "si tienes tarjeta de crédito", "si trabajas con contrato"),
2_esta_pasando_ahorita (por qué importa HOY: la temporada, un cambio reciente, una queja que
se repite; la regla puede ser vieja), 3_algo_no_cuadra (lo que te dicen contra lo que dice
la regla), 4_coraje (que te cobren o te nieguen algo a lo que tienes derecho),
5_se_puede_grabar, 6_hace_hablar ("¿a ti te lo han cobrado?") y 7_valor_practico (aquí es
el centro del video: los pasos).

VERIFICACIÓN (si un dato no se puede verificar, NO va)
1. Abre las fuentes (con el comando buscar; WebFetch solo si no lo tienes o no abre) y
   copia el artículo o el párrafo exacto. Los resúmenes del buscador inventan artículos.
2. Revisa que la regla siga vigente y que aplique en todo México; si cambia por estado, di
   en cuál aplica.
3. Los pasos salen de la página de la autoridad (requisitos, teléfono, plazo), no de una
   nota.
4. Anota en "_schema.fuentes" cada URL con lo que dice, y en "_schema.restriccion_etica" lo
   que decidiste NO usar y por qué.
5. No repitas ninguno de los que YA ESTÁN HECHOS (lista al final).

ESTRUCTURA (9 planos, ids p00 a p08)
- p00 "gancho_hablado": MÁXIMO 12 PALABRAS. Lo que te cobran o te niegan y que no deberían:
  "Esa comisión que te cobra el banco no la puede cobrar."
- p01 "a_quien_le_toca": a quién le pasa, y la primera PREGUNTA directa antes del segundo
  diez ("¿A ti ya te la cobraron?"). Aquí NO va el "Te imaginas a quien…" de otras
  fórmulas.
- p02 "contexto": la situación, con el lugar exacto donde pasa o donde se reclama (la
  oficina, la ciudad) y la autoridad que la vigila.
- p03 "lo_que_te_dicen": lo que dice el cajero, el contrato o la costumbre.
- p04 "lo_que_dice_la_regla": la regla, con su ley y su artículo dichos en voz alta. Aquí
  va la segunda PREGUNTA directa ("¿Sabías que existía?").
- p05 "el_numero": cuánta gente o cuánto dinero, con su fuente.
- p06 "que_hacer": los pasos, en orden, con dónde, qué llevar, cuánto cuesta y el plazo.
- p07 "cierre_bucle": lo que todavía no te dicen (la letra chiquita de la letra chiquita, de
  qué depende, qué no cubre). Sin moraleja.
- p08 "identidad_cierre": "Aquí el dato mata al gato. ¿A ti te lo han cobrado? Cuéntamelo
  en los comentarios." Su visual: {"tipo": "grafico_movimiento", "descripcion": "Cartel de
  cierre del canal.", "prompt_ia": "", "busqueda_medios": ""}.
Reglas de la narración: español de México, de tú. Ninguna frase pasa de 20 palabras. Números
y años en palabras. Máximo DOS nombres propios por frase. Nada que empiece con "Tl". En los
primeros tres planos, el lugar exacto. Total: 120 a 190 palabras. Sin palabras de tiempo
relativo (hoy, ayer, este año): se dice el año o "sigue".

EVIDENCIA (sin imágenes de IA)
"evidencia" es una lista; cada plano (p00 a p07) lleva en visual.evidencia 1 a 3 ids. Mínimo
TRES piezas reales más 2 o 3 fichas, y OBLIGATORIO un "documento": la regla misma (la ley con
su artículo, la NOM, la página de la autoridad).
- {"id": "e1", "tipo": "documento", "url": "...", "fuente": "..."}: la regla. Para un PDF
  agrega "pagina": n y, si el artículo está a media página, "desde": 0.6, "fraccion": 0.85.
  Que sea el PDF de la ley (diputados.gob.mx/LeyesBiblio) o del DOF (dof.gob.mx), o la página
  de CONDUSEF/IMSS/SAT. NO uses www.gob.mx (comunicados de PROFECO y demás): a la captura le
  sale una página "Challenge Validation" y la pieza se pierde (06/11/2026). El comunicado
  puede quedar como fuente de una ficha.
- {"id": "e2", "tipo": "prensa", "url": "...", "fuente": "Medio, DD/MM/AAAA"}: se captura el
  titular, así que el titular tiene que nombrar el tema.
- {"id": "e3", "tipo": "lugar" | "persona", "wikimedia": "File:Nombre exacto.jpg"}: un archivo
  que verificaste que existe. NO uses "buscar_wikimedia".
- {"id": "f1", "tipo": "ficha", "titulo": "QUÉ HACER", "renglones": ["1. ...", "2. ..."],
  "fuente": "..."}: los pasos van en una ficha, en el plano p06.
De p00 a p07 el visual.tipo es SIEMPRE "archivo_historico" con "motion": "calm"; solo p08
lleva "grafico_movimiento".

FORMATO DE CADA GUION
Escríbelo en C:\Android_in\<slug>\guion.json, con slug "guion-notedicen-" + palabras cortas
del tema (minúsculas y guiones). Además de lo de siempre ("titulo", "gancho", "claves",
"descripcion", "hashtags", "evidencia", "planos"), el "_schema" lleva:
  "regla": {"que_dice": "la regla en una frase", "fuente": "ley o NOM con su artículo",
            "url": "...", "vigente": "fecha de la última reforma o publicación"},
  "lo_que_te_dicen": "lo que dice el cajero, el contrato o la costumbre",
  "a_quien_le_toca": "...",
  "pasos": ["1. ... (fuente)", "2. ... (fuente)"],
  "de_que_depende": "de qué depende que aplique, o 'aplica igual para todos'",
  "numero": {"cifra": "...", "fuente": "institución y año"} (o {"cifra": null, "por_que":
             "no hay cifra oficial"}),
  "condiciones": {"1_te_afecta": "...", "2_esta_pasando_ahorita": "...", "3_algo_no_cuadra":
                  "...", "4_coraje": "...", "5_se_puede_grabar": "...", "6_hace_hablar": "...",
                  "7_valor_practico": "..."},
  "fuentes": {...}, "restriccion_etica": "...", "vigencia": "perenne"
Y en "plus" (en la raíz), OBLIGATORIO "contradiccion":
  {"plano": "p04", "arriba": {"titulo": "LO QUE TE DICEN", "renglones": ["...", "..."]},
   "abajo": {"titulo": "LO QUE DICE LA LEY", "renglones": ["...", "..."]},
   "abajo_en": "<una palabra de la narración de p04>", "resaltar": "<un renglón de abajo, igual>",
   "fuente": "Ley o institución, artículo"}
  2 o 3 renglones por bloque, máximo 36 letras.
  "mapa" SIEMPRE: {"plano": "p02", "consulta": "Procuraduría Federal del Consumidor, Ciudad de
     México", "etiqueta": "PROFECO · CDMX"}. "plano": donde la voz nombra el lugar;
     "consulta": como se buscaría en un mapa (calle, colonia o edificio, y la ciudad), NUNCA
     vacía; "etiqueta": máximo 32 letras.
  "contador" como siempre, si aplica.
  "portada" SIEMPRE: {"texto": "3 a 5 PALABRAS EN MAYÚSCULAS", "resalta": "1 o 2 de ellas"}
     (portada del perfil: lo que no te dicen, p. ej. "ESA COMISIÓN ES ILEGAL").

AL TERMINAR responde SOLO este bloque JSON:
{"guiones": [{"slug": "...", "titulo": "...", "resumen_hechos": "2 líneas con la regla y su
fuente", "pasos": "en una línea, qué hace quien ve"}]}
""".strip()


BUSCAR_TEMA = r"""
PRIMERO, QUÉ NO TE DICEN (antes de escribir nada)
No te dieron tema: búscalo. Encuentra <<CUANTOS>> cobros, reglas o derechos que le toquen a
casi cualquiera en México y que casi nadie conozca: bancos y tarjetas, luz, agua, teléfono e
internet, tiendas y garantías, restaurantes, vuelos y autobuses, trabajo (aguinaldo,
vacaciones, finiquito, horas extra), IMSS, Infonavit y Afore, SAT, renta, escuelas, multas de
tránsito, trámites.
Prefiere lo que la gente ya está preguntando (una temporada: aguinaldo en diciembre, vuelos
en vacaciones, regreso a clases; una queja que se repite en redes; un cambio reciente de la
regla) y lo que tiene una autoridad a la que se puede ir.
NO tomes: consejos de inversión, "trucos" sin regla detrás, temas de salud que pidan un
médico, ni nada donde no puedas decir el artículo.
Antes de escribir, dime en una línea por tema: qué no te dicen, qué regla lo dice (ley y
artículo) y qué hace quien ve. Luego escribe los <<CUANTOS>> guiones.
""".strip()


def instruccion(n: int, tema: str | None, ya_hechos: str, ligera: bool = False) -> str:
    """El prompt del lote. Sin `tema`, Claude busca primero qué no te dicen."""
    from dato_mata_gato_bot import instruccion_cercania

    if tema:
        descripcion = (f"{tema}. Investiga qué dice la regla (ley y artículo), si sigue vigente "
                       "y qué tiene que hacer quien ve para reclamarlo.")
    else:
        descripcion = BUSCAR_TEMA.replace("<<CUANTOS>>", str(n))
    texto = INSTRUCCION.replace("<<N>>", str(n)).replace("<<TEMA>>", descripcion)
    if ligera:
        texto = texto.replace("\nAL TERMINAR responde",
                              instruccion_cercania.COMO_TRABAJAR + "\nAL TERMINAR responde")
    return texto + instruccion_cercania.PUBLICAR + "\n\nYA ESTÁN HECHOS -- no repitas ninguno: " + ya_hechos


# "te van a devolver", "gana seguro": el video no promete el resultado.
_PROMESA = re.compile(r"\b(te (lo |la |los |las )?(van a|tienen que) (devolver|pagar|regresar) seguro|"
                      r"gana[sn]? seguro|garantizado|100 ?% seguro|sin falta te)\b", re.IGNORECASE)
# Adjetivos contra una empresa que necesitan una resolución detrás.
_ACUSACION = re.compile(r"\b(te roban|es un fraude|estafa|ladrones|rateros)\b", re.IGNORECASE)


def _vacio(x) -> bool:
    return not str(x or "").strip()


def problemas(guion: dict) -> list[str]:
    """Lo propio de esta fórmula, sin Claude (lo común lo revisa problemas_cercania)."""
    out = []
    schema = guion.get("_schema") or {}
    regla = schema.get("regla") or {}
    faltan = [k for k in ("que_dice", "fuente", "url", "vigente") if _vacio(regla.get(k))]
    if faltan:
        out.append(f'en "_schema.regla" falta: {", ".join(faltan)}. Sin la regla con su artículo '
                   "y su vigencia no hay video: cambia de tema")
    elif not re.search(r"\d", str(regla.get("fuente", ""))):
        out.append('"_schema.regla.fuente" no trae el artículo o el número de la norma '
                   '("Ley Federal de Protección al Consumidor, artículo 10")')
    for k in ("lo_que_te_dicen", "a_quien_le_toca", "de_que_depende"):
        if _vacio(schema.get(k)):
            out.append(f'falta "_schema.{k}"')
    pasos = [p for p in schema.get("pasos") or [] if not _vacio(p)]
    if len(pasos) < 2:
        out.append('"_schema.pasos" necesita por lo menos dos pasos concretos (a dónde ir, qué '
                   "pedir, plazo), cada uno con su fuente")
    numero = schema.get("numero")
    if not isinstance(numero, dict) or (_vacio(numero.get("cifra")) and _vacio(numero.get("por_que"))):
        out.append('falta "_schema.numero": la cifra con su fuente, o por qué no hay cifra oficial')
    elif not _vacio(numero.get("cifra")) and _vacio(numero.get("fuente")):
        out.append('"_schema.numero" trae cifra sin fuente')
    if not any(e.get("tipo") == "documento" for e in guion.get("evidencia", [])):
        out.append('falta una evidencia "documento": la regla se enseña en pantalla')
    if not any(e.get("tipo") == "ficha" for e in guion.get("evidencia", [])):
        out.append('falta la ficha "QUÉ HACER" con los pasos')
    if not ((guion.get("plus") or {}).get("contradiccion") or {}).get("arriba"):
        out.append('falta "plus.contradiccion" (LO QUE TE DICEN / LO QUE DICE LA LEY)')
    narracion = " ".join(p.get("narracion", "") for p in guion.get("planos", []))
    if (m := _PROMESA.search(narracion)):
        out.append(f'la voz dice "{m.group(0)}": no se promete el resultado; di "tienes derecho a '
                   'pedirlo" o "puedes reclamarlo ante…"')
    if (m := _ACUSACION.search(narracion)):
        out.append(f'la voz dice "{m.group(0)}": contra una empresa va un dato público (quejas, '
                   "sanción, resolución), no un adjetivo")
    return out
