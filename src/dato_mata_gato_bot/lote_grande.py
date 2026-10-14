"""Lotes grandes: muchos videos variados, archivados en disco sin publicar.

Un lote grande NO es un lote normal más largo. Tres diferencias, y las tres
son a propósito:

- **Variedad de formato.** Se reparte entre los formatos de crimen de
  `formatos.py` y los mitos, en vez de ser todo crimen clásico. Sin trivias
  desde el 28/09/2026 (ver `formatos.repartir`).
- **Variedad de presentador.** Uno de cada diez lleva avatar, rotando entre
  los tres.
- **No se publica nada.** Los videos se archivan en `lotes/<fecha>/` con el
  nombre corto del caso. No se suben a Drive ni entran al calendario: son
  material para revisar y publicar a mano.

El costo: un video normal son ~15 minutos de máquina y uno con presentador
~50. Está pensado para dejarlo corriendo, no para esperarlo.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dato_mata_gato_bot import avatar_presentador

logger = logging.getLogger(__name__)

CARPETA_LOTES = Path(r"C:\Android_in\lotes")

# Uno de cada diez videos lleva presentador. Era uno de cada cinco hasta el
# 28/09/2026, cuando el usuario pidió bajar su presencia. Además, desde ese día
# el true crime sin presentador usa otra voz (pipeline.voz_de_true_crime) y el
# presentador sigue con la de Javier: menos presentador, menos mezcla de voces.
CADA_CUANTOS_AVATAR = 10


@dataclass
class Plan:
    """Qué se va a generar, decidido ANTES de empezar."""
    carpeta: Path
    tareas: list[tuple[str, int | None]] = field(default_factory=list)

    @property
    def con_avatar(self) -> int:
        return sum(1 for _, a in self.tareas if a is not None)

    def resumen(self) -> str:
        # Un true crime sin presentador tarda ~40 min desde el 28/09/2026: su
        # voz va con num_step=32 (ver pipeline.voz_de_true_crime), ~4.5 min
        # por plano. Medido con Tierra Blanca: 8 planos, ~37 min de voz.
        crimen = sum(1 for s, a in self.tareas if s.startswith("guion-") and a is None)
        horas = (len(self.tareas) * 15 + crimen * 25 + self.con_avatar * 35) / 60
        return (f"{len(self.tareas)} videos, {self.con_avatar} con presentador\n"
                f"carpeta: {self.carpeta}\n"
                f"tiempo estimado: ~{horas:.0f} horas")


def carpeta_del_dia(hoy: date | None = None) -> Path:
    return CARPETA_LOTES / (hoy or date.today()).strftime("%Y-%m-%d")


ENTRADA_GUIONES = Path(r"C:\Android_in")

# Un video de 15 segundos no justifica media hora de sincronizado de labios, y
# en una trivia el presentador taparía las tarjetas de pregunta. El avatar va
# a los videos de caso, que son los que tienen narración sostenida.
_MIN_PLANOS_PARA_AVATAR = 5


def admite_avatar(slug: str, entrada: Path | None = None) -> bool:
    """¿A este video le conviene un presentador?

    Se lee el guion en vez de confiar en el nombre: los formatos cortos no
    tienen prefijo propio y solo se distinguen por la cantidad de planos.
    Ante la duda (guion ilegible) se responde que NO, para no gastar treinta
    minutos de GPU a ciegas.
    """
    if slug.startswith("trivia"):
        return False
    # Un mito tampoco: dura unos 2:15, así que MuseTalk se llevaría casi una
    # hora de GPU, y el presentador en la esquina taparía la dramatización,
    # que es justo lo que ese formato vende.
    if slug.startswith("mito"):
        return False
    ruta = (entrada or ENTRADA_GUIONES) / slug / "guion.json"
    try:
        guion = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return len(guion.get("planos") or []) >= _MIN_PLANOS_PARA_AVATAR


def repartir_voces(plan: "Plan", entrada: Path | None = None) -> dict[str, str]:
    """Prueba de voces (11/10/2026): alterna Fish 3 y la voz nueva de Javier,
    una y una, entre los true crime SIN presentador del lote, y lo deja escrito
    en el guion (`voz_narrador`) para que el pipeline lo respete.

    El que ya trae voz se respeta: un lote retomado no cambia la voz de lo que
    ya salió. Sin el perfil de Javier configurado no se escribe nada.
    """
    from dato_mata_gato_bot import pipeline

    if not pipeline.VOCES_CRIMEN["javier"]():
        return {}
    base = entrada or pipeline.ANDROID_IN
    repartidas: dict[str, str] = {}
    turno = 0
    for slug, avatar in plan.tareas:
        if avatar is not None or not slug.startswith("guion-"):
            continue
        ruta = base / slug / "guion.json"
        try:
            guion = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if guion.get("voz_narrador") not in pipeline.VOCES_CRIMEN:
            guion["voz_narrador"] = "fish3" if turno % 2 == 0 else "javier"
            ruta.write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
        repartidas[slug] = guion["voz_narrador"]
        turno += 1
    return repartidas


def planificar(slugs: list[str], hoy: date | None = None,
               entrada: Path | None = None, con_avatar: bool = True) -> Plan:
    """Decide qué slug lleva qué avatar, y dónde se archiva todo.

    Los avatares rotan 0, 1, 2 para que ninguno domine el lote, y se reparten
    solo entre los videos que los admiten (ver `admite_avatar`). La asignación
    es por POSICIÓN y no al azar: el mismo lote planificado dos veces da el
    mismo resultado, así que una corrida que se cortó se puede repetir sin que
    cambien los videos que ya salieron.

    OJO con lotes chicos: con uno de cada diez, un lote de 9 no tiene
    presentador y uno de 12 tiene UNO solo. Los tres avatares aparecen recién
    a partir de 30. Es una limitación real del tamaño, no un error.
    """
    if not con_avatar:
        # Lote de /lotefish3: todo con la voz de Fish 3 y el logo fijo.
        return Plan(carpeta=carpeta_del_dia(hoy), tareas=[(s, None) for s in slugs])
    disponibles = avatar_presentador.avatares_disponibles() or [0]
    elegibles = [s for s in slugs if admite_avatar(s, entrada)]
    # Se eligen repartidos a lo largo del lote y no los primeros, para que el
    # presentador no se amontone al principio.
    cuantos = len(slugs) // CADA_CUANTOS_AVATAR
    paso = max(1, len(elegibles) // cuantos) if cuantos else 0
    con_avatar = {s: disponibles[i % len(disponibles)]
                  for i, s in enumerate(elegibles[::paso][:cuantos])} if cuantos else {}
    return Plan(
        carpeta=carpeta_del_dia(hoy),
        tareas=[(s, con_avatar.get(s)) for s in slugs],
    )
