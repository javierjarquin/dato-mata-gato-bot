"""Prueba de un mes con todos los formatos (06/11/2026)."""

import asyncio
import json
from types import SimpleNamespace

from dato_mata_gato_bot import fabrica, formatos, instruccion_notedicen


def test_cinco_son_cinco_formatos_distintos():
    """Javier: "si te pido 5 es uno de cada formato"."""
    cinco = fabrica.repartir_todos(5)
    assert len(set(cinco)) == 5
    ocho = fabrica.repartir_todos(8)
    assert sorted(ocho) == sorted(fabrica.FORMATOS_TODOS)


def test_la_rotacion_sigue_donde_quedo_el_lote_anterior(tmp_path, monkeypatch):
    monkeypatch.setattr(fabrica, "RAIZ", tmp_path)
    viejo = {"lote": "todos-1", "formato": "todos",
             "videos": {f"s{i}": {"formato": f} for i, f in enumerate(fabrica.repartir_todos(5))}}
    (tmp_path / "todos-1").mkdir()
    (tmp_path / "todos-1" / "estado.json").write_text(json.dumps(viejo), encoding="utf-8")
    # Un lote de redes no cuenta en la rotación del mes.
    (tmp_path / "redes-1").mkdir()
    (tmp_path / "redes-1" / "estado.json").write_text(json.dumps(
        {"lote": "redes-1", "formato": "redes", "videos": {"x": {"formato": "viral"}}}), encoding="utf-8")
    hechos = fabrica.conteo_formatos()
    siguientes = fabrica.repartir_todos(3, hechos)
    assert not set(siguientes) & set(viejo_f["formato"] for viejo_f in viejo["videos"].values())


def test_un_formato_sin_temas_frescos_cede_su_turno():
    sin_viral = fabrica.repartir_todos(8, {}, {"viral"})
    assert "viral" not in sin_viral[:7]


def test_las_partes_de_la_serie_salen_en_orden_o_nada():
    assert fabrica.partes_de_serie(["guion-serie-x-parte-3", "guion-serie-x-parte-1",
                                    "guion-serie-x-parte-2"]) == [
        "guion-serie-x-parte-1", "guion-serie-x-parte-2", "guion-serie-x-parte-3"]
    assert fabrica.partes_de_serie(["guion-serie-x-parte-1", "guion-serie-x-parte-3"]) is None
    assert "SERIE EN TRES PARTES" in formatos.instruccion_de(formatos.SERIE)
    assert formatos.SERIE not in [f.clave for f in formatos.ORDEN]


def test_la_serie_suelta_una_parte_por_turno(tmp_path, monkeypatch):
    """Se escribe entera una vez; cada turno de la serie suelta la siguiente parte."""
    from dato_mata_gato_bot import bot

    monkeypatch.setattr(fabrica, "COLA_SERIE", tmp_path / "_serie_cola.json")
    monkeypatch.setattr(bot, "_sesion_nueva", lambda: ("s1", True))
    escritas = []

    async def crimen(avisador, sid, nueva, cantidad, desc, formato):
        escritas.append((cantidad, formato))
        return [{"slug": f"guion-serie-caso-parte-{i}"} for i in (1, 2, 3)]

    monkeypatch.setattr(bot, "_guiones_de_crimen", crimen)
    av = SimpleNamespace(message=SimpleNamespace(reply_text=None))
    salen = [asyncio.run(fabrica._guiones_serie(av, None, 1))[0][0]["slug"] for _ in range(4)]
    assert salen == ["guion-serie-caso-parte-1", "guion-serie-caso-parte-2",
                     "guion-serie-caso-parte-3", "guion-serie-caso-parte-1"]
    assert escritas == [(3, "serie"), (3, "serie")]


def test_la_tanda_registra_el_formato_de_cada_guion(tmp_path, monkeypatch):
    monkeypatch.setattr(fabrica, "RAIZ", tmp_path)
    estado = fabrica.crear("todos-x", 5, "todos", por_tanda=2)
    pedidos = []
    for formato, (funcion, _, _) in fabrica.FORMATOS_TODOS.items():
        async def escribir(av, tema, cantidad, ligera=None, formato=formato):
            pedidos.append(formato)
            return [{"slug": f"guion-{formato}-{i}"} for i in range(cantidad)], []
        monkeypatch.setattr(fabrica, funcion, escribir)
    nuevos, limite = fabrica.escribir_tanda(estado)
    assert limite is None and len(nuevos) == 2 and len(set(pedidos)) == 2
    assert {estado["_formatos"][s] for s in nuevos} == set(pedidos)


def _notedicen(**cambios) -> dict:
    g = {
        "_schema": {
            "regla": {"que_dice": "No pueden cobrar comisión por consultar saldo en ventanilla",
                      "fuente": "Disposiciones de Banxico, artículo 9", "url": "https://www.banxico.org.mx/x",
                      "vigente": "2024"},
            "lo_que_te_dicen": "Es la política del banco",
            "a_quien_le_toca": "quien tiene cuenta de débito",
            "pasos": ["1. Pide la aclaración en la sucursal (CONDUSEF)", "2. Si no, queja en CONDUSEF"],
            "de_que_depende": "aplica igual para todos",
            "numero": {"cifra": "dos millones de quejas", "fuente": "CONDUSEF, 2025"},
        },
        "evidencia": [{"id": "e1", "tipo": "documento"}, {"id": "f1", "tipo": "ficha"}],
        "plus": {"contradiccion": {"arriba": {"titulo": "LO QUE TE DICEN"}}},
        "planos": [{"id": "p04", "narracion": "Tienes derecho a pedirlo ante la CONDUSEF."}],
    }
    g.update(cambios)
    return g


def test_lo_que_no_te_dicen_pide_la_regla_los_pasos_y_no_promete():
    assert instruccion_notedicen.problemas(_notedicen()) == []
    sin_articulo = _notedicen()
    sin_articulo["_schema"]["regla"]["fuente"] = "una ley"
    assert "artículo" in " ".join(instruccion_notedicen.problemas(sin_articulo))
    un_paso = _notedicen()
    un_paso["_schema"]["pasos"] = ["1. reclama"]
    assert "dos pasos" in " ".join(instruccion_notedicen.problemas(un_paso))
    promete = _notedicen(planos=[{"id": "p06", "narracion": "Te lo van a devolver seguro."}])
    assert "no se promete" in " ".join(instruccion_notedicen.problemas(promete))
    acusa = _notedicen(planos=[{"id": "p03", "narracion": "Ese banco te roban cada mes."}])
    assert "dato público" in " ".join(instruccion_notedicen.problemas(acusa))
    texto = instruccion_notedicen.instruccion(1, None, "")
    assert "LO QUE NO TE DICEN" in texto and "guion-notedicen-" in texto
