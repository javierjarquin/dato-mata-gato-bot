"""Fórmula de LA COMPARATIVA: cómo se hace ahora / cómo se hacía antes (o en
otro lado) / cuál funciona mejor y por qué (20/10/2026, Javier: "hablar de lo
bueno o lo malo de las gubernaturas de México vs otras... se pone una
situación, se explica cómo se hace actual, cómo se hacía antes, y cuál está o
estaba mejor y por qué").

Va en la mezcla de /lotegrande: uno de cada cinco (`fabrica.MEZCLA_REDES`).

Lo que la separa de la propaganda es que el veredicto sale de UN indicador
medido igual en los dos lados, de una fuente que no es ninguno de los dos
gobiernos cuando se puede, y con lo que el dato no mide dicho en voz alta.
"""

import re

INSTRUCCION = r"""
Vas a escribir <<N>> guiones de video corto (45 a 75 segundos) para el canal Dato Mata Gato.

EL TEMA
<<TEMA>>

DE QUÉ VA ESTA FÓRMULA: "¿QUIÉN LO HACE MEJOR?"
Una situación concreta que le toca a la gente (el agua, la seguridad, el transporte, un
trámite, un hospital, un programa, la basura, las calles) y DOS formas de resolverla:
  - cómo se hace AHORA, con el gobierno que hoy está (estado o municipio, con su nombre y
    desde cuándo);
  - cómo se hacía ANTES (el gobierno anterior del mismo lugar) o cómo se hace en OTRO lado
    (otro estado de México, u otro país si el ejemplo es claro).
Y la pregunta que mueve el video: ¿cuál funciona o funcionaba mejor, y POR QUÉ?
Lo bueno y lo malo de cada lado: no es un video a favor ni en contra de nadie.

LOS CANDADOS (sin uno de ellos no hay video; cámbiate de tema)
1. MISMA VARA. El veredicto sale de UN indicador medido IGUAL en los dos lados: la misma
   fuente, la misma unidad y periodos comparables. Tasas por cada 100 mil habitantes, no
   totales; pesos del mismo año (o porcentajes), no pesos corrientes; años completos o el
   mismo tramo de cada gobierno. Fuentes que sirven: INEGI (ENVIPE, ENIGH, censos), CONEVAL,
   SESNSP, IMCO, México Evalúa, Auditoría Superior, CONAGUA, los informes oficiales de cada
   gobierno (y si el dato sale del mismo gobierno que sale ganando, se dice).
2. EL VEREDICTO SALE DEL DATO. "Mejor" solo en lo que el indicador mide, y se dice qué no
   mide. Si el dato no da un ganador claro, el veredicto es "depende" o "empate", y se dice
   así: también es un buen video.
3. LA PRUEBA DEL ESPEJO. Si el ganador fuera del otro partido, ¿escribirías el guion igual,
   con las mismas palabras? Si no, reescríbelo. Cada lado lleva por lo menos UNA cosa que le
   salió bien y una que le salió mal, si existe; si de verdad no existe, di por qué.
4. EL PORQUÉ TIENE FUENTE. Explica el mecanismo (qué cambió: el presupuesto, la regla, la
   concesión, la gente a cargo) con su fuente. Si solo coincide en el tiempo, se dice
   "coincide con", nunca "por culpa de" ni "gracias a".
5. SIN CAMPAÑA. Nada de pedir el voto, adjetivos de partido ("el mal gobierno", "la
   transformación"), ni apodos. Los gobiernos se nombran por su titular, su cargo y su
   periodo ("el gobierno de Carlos Joaquín, de dos mil dieciséis a dos mil veintidós").

LAS PIEZAS DE LA FÓRMULA DE CERCANÍA SIGUEN (en "_schema.condiciones")
1_te_afecta, 2_esta_pasando_ahorita (aquí: por qué esto importa HOY, aunque la comparación
sea de años), 3_algo_no_cuadra (lo que el discurso dice contra lo que el dato muestra),
4_coraje, 5_se_puede_grabar, 6_hace_hablar (la gente compara con lo que vivió: "con el de
antes sí llegaba el agua") y, si se puede, 7_valor_practico.

VERIFICACIÓN (si un dato no se puede verificar, NO va)
1. Abre las fuentes (con el comando buscar; WebFetch solo si no lo tienes o no abre) y saca las dos cifras de la MISMA tabla o serie. Los
   resúmenes del buscador inventan cifras.
2. Lo que solo dice una fuente va atribuido en la narración ("según el INEGI…").
3. Si las dos cifras no se miden igual, no las compares: busca otro indicador.
4. Anota en "_schema.fuentes" cada URL con lo que dice, y en "_schema.restriccion_etica" lo
   que decidiste NO usar y por qué.
5. No repitas ninguno de los que YA ESTÁN HECHOS (lista al final).

ESTRUCTURA (9 planos, ids p00 a p08)
- p00 "gancho_hablado": MÁXIMO 12 PALABRAS. El contraste, con el lugar: "En Quintana Roo el
  agua llegaba de una forma y hoy de otra. Una funcionó mejor." Ningún año dicho.
- p01 "las_dos_versiones": aquí NO va el "Te imaginas a quien…" de otras fórmulas (Javier,
  20/10/2026: en una comparación no aplica). Se le dice a quien ve que YA VIVIÓ los dos
  lados, o que los conoce de cerca, y se le pregunta con cuál le fue mejor, antes del
  segundo diez:
     "Si llevas más de seis años en Cancún, ya te tocaron las dos. ¿Con cuál te fue mejor?"
     "Si tienes familia en Mérida, sabes que allá no es igual. ¿Allá sí llega?"
  El tiempo va en años vividos, no en fechas ("más de seis años"), para que envejezca bien.
- p02 "contexto": la situación y a quién le toca, con el lugar exacto.
- p03 "como_se_hace_ahora": cómo funciona hoy, quién lo decidió y desde cuándo.
- p04 "como_se_hacia_antes": cómo se hacía antes, o cómo se hace en el otro lugar. Aquí va
  la segunda PREGUNTA directa ("¿Tú cuál prefieres?").
- p05 "la_medicion": el MISMO indicador en los dos lados, cifra contra cifra, con su fuente.
- p06 "el_porque": por qué uno funciona mejor (el mecanismo, con fuente), lo bueno y lo malo
  de cada lado, y lo que el dato NO mide.
- p07 "cierre_bucle": el veredicto con su condición ("en esto, ganó…; en esto otro, no") y
  lo que ninguno de los dos gobiernos ha explicado. Sin moraleja.
- p08 "identidad_cierre": "Aquí el dato mata al gato. ¿A ti te fue mejor con [A]? Cuéntamelo
  en los comentarios." (pregunta de sí o no: "¿con cuál te quedas, A o B?" la voz la lee sin
  tono de pregunta). Su visual: {"tipo": "grafico_movimiento", "descripcion":
  "Cartel de cierre del canal.", "prompt_ia": "", "busqueda_medios": ""}.
Reglas de la narración: español de México, de tú. Ninguna frase pasa de 20 palabras. Números
y años en palabras. Máximo DOS nombres propios por frase. Nada que empiece con "Tl". En los
primeros tres planos, el lugar exacto. Total: 120 a 190 palabras. Sin palabras de tiempo
relativo (hoy, ayer, este año): se dice el año o "sigue".

EVIDENCIA (sin imágenes de IA)
"evidencia" es una lista; cada plano (p00 a p07) lleva en visual.evidencia 1 a 3 ids. Mínimo
TRES piezas reales más 2 o 3 fichas, y OBLIGATORIO un "documento": la fuente del indicador.
- {"id": "e1", "tipo": "prensa", "url": "...", "fuente": "Medio, DD/MM/AAAA"}: se captura el
  titular, así que el titular tiene que nombrar el caso.
- {"id": "e2", "tipo": "documento", "url": "...", "fuente": "..."}: la tabla o el informe
  del indicador. Para un PDF agrega "pagina": n y, si el dato está a media página,
  "desde": 0.6, "fraccion": 0.85.
- {"id": "e3", "tipo": "lugar" | "persona", "wikimedia": "File:Nombre exacto.jpg"}: un archivo
  que verificaste que existe. NO uses "buscar_wikimedia".
- {"id": "f1", "tipo": "ficha", "titulo": "...", "renglones": ["...", "..."], "fuente": "..."}.
De p00 a p07 el visual.tipo es SIEMPRE "archivo_historico" con "motion": "calm"; solo p08
lleva "grafico_movimiento".

FORMATO DE CADA GUION
Escríbelo en C:\Android_in\<slug>\guion.json, con slug "guion-comparativa-" + palabras cortas
del tema (minúsculas y guiones). Además de lo de siempre ("titulo", "gancho", "claves",
"descripcion", "hashtags", "evidencia", "planos"), el "_schema" lleva:
  "comparacion": {"situacion": "...",
                  "lado_a": {"quien": "titular y cargo", "periodo": "AAAA-AAAA", "como": "..."},
                  "lado_b": {"quien": "...", "periodo": "...", "como": "..."}},
  "indicador": {"nombre": "...", "unidad": "por cada 100 mil, %, pesos de AAAA…",
                "fuente": "institución, tabla o serie", "a": "cifra del lado A con su periodo",
                "b": "cifra del lado B con su periodo"},
  "veredicto": {"mejor": "a" | "b" | "empate" | "depende", "por_que": "el mecanismo, con
                fuente", "lo_que_no_mide": "..."},
  "balance": {"bien_a": "...", "mal_a": "...", "bien_b": "...", "mal_b": "..."},
  "prueba_del_espejo": "por qué escribirías lo mismo si el ganador fuera del otro partido",
  "condiciones": {"1_te_afecta": "...", "2_esta_pasando_ahorita": "...", "3_algo_no_cuadra":
                  "...", "4_coraje": "...", "5_se_puede_grabar": "...", "6_hace_hablar": "..."},
  "fuentes": {...}, "restriccion_etica": "...", "vigencia": "perenne"
Y en "plus" (en la raíz), OBLIGATORIO "contradiccion" con los dos lados:
  {"plano": "p05", "arriba": {"titulo": "ANTES", "renglones": ["...", "..."]},
   "abajo": {"titulo": "AHORA", "renglones": ["...", "..."]},
   "abajo_en": "<una palabra de la narración de p05>", "resaltar": "<un renglón de abajo, igual>",
   "fuente": "Institución, DD/MM/AAAA"}
  (o "AQUÍ" / "ALLÁ" si comparas lugares). 2 o 3 renglones por bloque, máximo 36 letras.
  "mapa" SIEMPRE: {"plano": "p02", "consulta": "Palacio Legislativo de San Lázaro, Ciudad de
     México", "etiqueta": "SAN LÁZARO · CDMX"}. "plano": donde la voz nombra el lugar;
     "consulta": como se buscaría en un mapa (calle, colonia o edificio, y la ciudad), NUNCA
     vacía; "etiqueta": máximo 32 letras.
  "contador" como siempre, si aplica.
  "portada" SIEMPRE: {"texto": "3 a 5 PALABRAS EN MAYÚSCULAS", "resalta": "1 o 2 de ellas"}
     (portada del perfil: la diferencia que sorprende, p. ej. "AQUÍ RINDE MENOS").

AL TERMINAR responde SOLO este bloque JSON:
{"guiones": [{"slug": "...", "titulo": "...", "resumen_hechos": "2 líneas con la comparación y
su fuente", "veredicto": "en una línea: quién gana, en qué, y qué no mide"}]}
""".strip()


BUSCAR_TEMA = r"""
PRIMERO, QUÉ COMPARAR (antes de escribir nada)
No te dieron tema: búscalo. Encuentra <<CUANTOS>> situaciones donde un gobierno de México
(estatal sobre todo; también municipal) haga algo distinto que el gobierno anterior, o que
otro estado u otro país, y donde exista UN indicador medido igual en los dos lados.
Prefiere lo que la gente ya está discutiendo (un cambio reciente, un informe de gobierno, una
queja que se repite en redes) y lo que le toca a casi todos: agua, seguridad, transporte,
salud, basura, trámites, precios regulados.
NO tomes: chismes de políticos, encuestas de popularidad como indicador, comparaciones sin
la misma vara, ni temas donde solo hay discurso y no hay dato.
Antes de escribir, dime en una línea por tema: qué se compara, cuál es el indicador y de qué
fuente sale. Luego escribe los <<CUANTOS>> guiones.
""".strip()


def instruccion(n: int, tema: str | None, ya_hechos: str, ligera: bool = False) -> str:
    """El prompt del lote. Sin `tema`, Claude busca primero qué comparar."""
    from dato_mata_gato_bot import instruccion_cercania

    if tema:
        descripcion = (f"{tema}. Investiga cómo se hace ahora, cómo se hacía antes (o en otro "
                       "lugar) y qué indicador lo mide igual en los dos lados.")
    else:
        descripcion = BUSCAR_TEMA.replace("<<CUANTOS>>", str(n))
    texto = INSTRUCCION.replace("<<N>>", str(n)).replace("<<TEMA>>", descripcion)
    if ligera:
        texto = texto.replace("\nAL TERMINAR responde",
                              instruccion_cercania.COMO_TRABAJAR + "\nAL TERMINAR responde")
    return texto + instruccion_cercania.PUBLICAR + "\n\nYA ESTÁN HECHOS -- no repitas ninguno: " + ya_hechos


VEREDICTOS = {"a", "b", "empate", "depende"}
_PARTIDISTAS = re.compile(r"\b(mal gobierno|la transformaci[oó]n|prian|chairos?|fifís?|vota por|"
                          r"no votes|narcogobierno)\b", re.IGNORECASE)


def _vacio(x) -> bool:
    return not str(x or "").strip()


def problemas(guion: dict) -> list[str]:
    """Lo propio de la comparativa, sin Claude (lo común lo revisa problemas_cercania)."""
    out = []
    schema = guion.get("_schema") or {}
    comp = schema.get("comparacion") or {}
    if _vacio(comp.get("situacion")):
        out.append('falta "_schema.comparacion.situacion": la situación que se compara')
    for lado in ("lado_a", "lado_b"):
        datos = comp.get(lado) or {}
        faltan = [k for k in ("quien", "periodo", "como") if _vacio(datos.get(k))]
        if faltan:
            out.append(f'en "_schema.comparacion.{lado}" falta: {", ".join(faltan)}')
    ind = schema.get("indicador") or {}
    faltan = [k for k in ("nombre", "unidad", "fuente", "a", "b") if _vacio(ind.get(k))]
    if faltan:
        out.append(f'en "_schema.indicador" falta: {", ".join(faltan)}. Sin la misma vara en los '
                   "dos lados no hay comparación: busca otro indicador o cambia de tema")
    ver = schema.get("veredicto") or {}
    if str(ver.get("mejor", "")).strip().lower() not in VEREDICTOS:
        out.append('"_schema.veredicto.mejor" tiene que ser "a", "b", "empate" o "depende"')
    for k in ("por_que", "lo_que_no_mide"):
        if _vacio(ver.get(k)):
            out.append(f'falta "_schema.veredicto.{k}"')
    bal = schema.get("balance") or {}
    faltan = [k for k in ("bien_a", "mal_a", "bien_b", "mal_b") if _vacio(bal.get(k))]
    if faltan:
        out.append(f'en "_schema.balance" falta: {", ".join(faltan)} (lo bueno y lo malo de cada '
                   'lado; si de verdad no hay, escribe por qué)')
    if _vacio(schema.get("prueba_del_espejo")):
        out.append('falta "_schema.prueba_del_espejo": ¿lo escribirías igual si el ganador fuera '
                   "del otro partido?")
    if not any(e.get("tipo") == "documento" for e in guion.get("evidencia", [])):
        out.append('falta una evidencia "documento": la fuente del indicador se enseña en pantalla')
    if not ((guion.get("plus") or {}).get("contradiccion") or {}).get("arriba"):
        out.append('falta "plus.contradiccion" con los dos lados (ANTES / AHORA o AQUÍ / ALLÁ)')
    narracion = " ".join(p.get("narracion", "") for p in guion.get("planos", []))
    if (m := _PARTIDISTAS.search(narracion)):
        out.append(f'la voz dice "{m.group(0)}": sin lenguaje de campaña; nombra a cada gobierno '
                   "por su titular, su cargo y su periodo")
    return out
