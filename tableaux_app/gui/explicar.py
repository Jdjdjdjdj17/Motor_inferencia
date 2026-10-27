# -*- coding: utf-8 -*-
"""Traducciones en lenguaje natural para fórmulas y ramas del tableau.

La idea es que la interfaz no dependa de símbolos ni de etiquetas técnicas:
cada fórmula se lee usando el texto de los átomos y cada rama se explica
como una pequeña historia de deducciones.
"""

from typing import List

from tableaux_app.core.formulas import (
    Formula, Atom, Not, And, Or, Imp, Iff, formula_a_string,
)


def _texto_atomo(f: Atom, dicc) -> str:
    info = dicc.atomos.get(f.id) if dicc else None
    if info is not None:
        return info.texto
    return f.texto or f.id


def _es_compuesta(f: Formula) -> bool:
    """True para fórmulas que conviene poner entre paréntesis."""
    if isinstance(f, Atom):
        return False
    if isinstance(f, Not) and isinstance(f.f, Atom):
        return False
    return True


def _operando(f: Formula, dicc) -> str:
    texto = formula_en_palabras(f, dicc)
    return f"({texto})" if _es_compuesta(f) else texto


def formula_en_palabras(f: Formula, dicc) -> str:
    """Devuelve la lectura de una fórmula usando los nombres de los átomos."""
    if isinstance(f, Atom):
        return _texto_atomo(f, dicc)

    if isinstance(f, Not):
        # Doble negación: se lee como una afirmación, no como un trabalenguas.
        if isinstance(f.f, Not):
            return "es verdad que " + _operando(f.f.f, dicc)
        interior = formula_en_palabras(f.f, dicc)
        if isinstance(f.f, Atom):
            return f"no {interior}"
        return f"no es cierto que ({interior})"

    if isinstance(f, And):
        return f"{_operando(f.left, dicc)} y {_operando(f.right, dicc)}"

    if isinstance(f, Or):
        return f"{_operando(f.left, dicc)} o {_operando(f.right, dicc)}"

    if isinstance(f, Imp):
        return f"si {_operando(f.left, dicc)}, entonces {_operando(f.right, dicc)}"

    if isinstance(f, Iff):
        return f"{_operando(f.left, dicc)} si y solo si {_operando(f.right, dicc)}"

    return formula_a_string(f)


def formula_y_lectura(f: Formula, dicc) -> str:
    """Texto técnico y su lectura natural, para la lista de reglas."""
    return f"{formula_a_string(f)}  —  {formula_en_palabras(f, dicc)}"


def _con_comillas(texto: str) -> str:
    return f"«{texto}»"


def _lista_formulas(formulas: List[Formula], dicc, conector: str = " y ") -> str:
    if not formulas:
        return "nada"
    return conector.join(_con_comillas(formula_en_palabras(f, dicc)) for f in formulas)


def _opcion(formulas: List[Formula], dicc) -> str:
    """Una opción de una bifurcación; si tiene varias fórmulas, las agrupa."""
    if not formulas:
        return "nada"
    if len(formulas) == 1:
        return _con_comillas(formula_en_palabras(formulas[0], dicc))
    return "(" + " y ".join(
        _con_comillas(formula_en_palabras(f, dicc)) for f in formulas
    ) + ")"


def _nuevas_del_nodo(nodo, tabla) -> List[Formula]:
    padre = tabla.nodes.get(nodo.parent_id)
    if padre is None:
        return []
    return nodo.formulas[len(padre.formulas):]


def _ya_estaba(f: Formula, padre, tabla) -> bool:
    if padre is None:
        return False
    return any(tabla.son_formulas_iguales(f, g) for g in padre.formulas)


def pasos_de_rama(rama, tabla, dicc) -> List[str]:
    """Pasos del camino raíz→hoja, explicados con los átomos.

    No usa etiquetas técnicas ni «izquierda/derecha»: cuenta qué regla se
    aplicó y qué alternativa se eligió en cada bifurcación.
    """
    pasos = []
    for nodo in rama["nodos"]:
        if nodo.generada_por is None:
            pasos.append("Empezamos con: " + _lista_formulas(
                nodo.formulas, dicc, conector="; "
            ) + ".")
            continue

        padre = tabla.nodes.get(nodo.parent_id)
        nuevas = _nuevas_del_nodo(nodo, tabla)
        origen = formula_en_palabras(nodo.generada_por, dicc)

        if nodo.lado:
            izq, der = tabla.expandir_beta(nodo.generada_por)
            opciones = f"{_opcion(izq, dicc)} o {_opcion(der, dicc)}"
            elegido = _opcion(nuevas, dicc)
            texto = (
                f"Para cumplir «{origen}» se abre en dos caminos: "
                f"{opciones}. En esta rama se toma {elegido}"
            )
            if nuevas and all(_ya_estaba(f, padre, tabla) for f in nuevas):
                texto += " (ya estaba en la rama; no agrega nada nuevo)"
            pasos.append(texto + ".")
        else:
            texto = f"De «{origen}» se deduce {_lista_formulas(nuevas, dicc)}"
            if nuevas and all(_ya_estaba(f, padre, tabla) for f in nuevas):
                texto += " (ya estaba en la rama; no agrega nada nuevo)"
            pasos.append(texto + ".")

    return pasos


def resultado_de_rama(rama, tabla, dicc) -> str:
    """Explica si la rama sirve o por qué se descarta."""
    if rama["estado"] == "cerrada":
        cierre = rama.get("cierre")
        if cierre:
            a, b = cierre
            return (
                "Esta rama se descarta: aparecen a la vez "
                f"«{formula_en_palabras(a, dicc)}» y "
                f"«{formula_en_palabras(b, dicc)}»."
            )
        return "Esta rama se descarta por una contradicción."

    return "Esta rama es posible: no hay contradicción."


def modelo_dict_en_palabras(modelo, dicc) -> str:
    """Convierte una asignación (letra → V/F/—) en una frase natural."""
    fijos = []
    libres = []
    for letra, valor in modelo.items():
        info = dicc.atomos.get(letra) if dicc else None
        texto = info.texto if info is not None else letra
        if valor == "V":
            fijos.append(f"sí {texto}")
        elif valor == "F":
            fijos.append(f"no {texto}")
        else:
            libres.append(texto)

    if fijos:
        frase = "En este modelo: " + ", ".join(fijos)
    else:
        frase = "En este modelo no se fija ningún átomo"

    if libres:
        if len(libres) == 1:
            frase += f"; {libres[0]} queda libre (puede ser sí o no)"
        else:
            frase += (
                "; " + " y ".join(libres)
                + " quedan libres (pueden ser sí o no)"
            )

    return frase + "."


def modelo_en_palabras(rama, tabla, dicc) -> str:
    return modelo_dict_en_palabras(tabla.asignacion_de_rama(rama, dicc), dicc)


def valores_de_rama(rama, tabla, dicc) -> str:
    """Valores compactos para referencia: p=F, q=F, r=libre."""
    asignacion = tabla.asignacion_de_rama(rama, dicc)
    return ", ".join(
        f"{letra}={'libre' if valor == '—' else valor}"
        for letra, valor in asignacion.items()
    )


def valores_de_modelo(modelo) -> str:
    return ", ".join(
        f"{letra}={'libre' if valor == '—' else valor}"
        for letra, valor in modelo.items()
    )


def tabla_de_atomos(dicc) -> str:
    """Línea compacta con las equivalencias de los átomos."""
    if dicc is None or not dicc.atomos:
        return "(sin átomos)"
    return ", ".join(
        f"{letra} = {info.texto}" for letra, info in dicc.atomos.items()
    )
