# -*- coding: utf-8 -*-
"""Caso de prueba mínimo del enunciado: comprueba que el árbol dé
2 ramas cerradas y 1 abierta con el modelo p=V, q=V, r=F."""
import sys

from tableaux_app.core.parser import texto_a_formulas
from tableaux_app.core.tableau import Tableau
from tableaux_app.core.formulas import formula_a_string

TEXTO = """Si es de día, entonces voy a trabajar.
Si llueve, entonces no voy a trabajar.
Es de día."""


def main() -> int:
    formulas, dicc = texto_a_formulas(TEXTO)

    print("=== FÓRMULAS ===")
    for i, f in enumerate(formulas):
        print(f"R{i + 1}: {formula_a_string(f)}")

    print("\n=== TABLA DE ÁTOMOS ===")
    for info in dicc.tabla():
        print(f"{info.id}: {info.texto}")

    t = Tableau(formulas)
    t.expandir()

    print("\n=== RAMAS ===")
    ramas = t.obtener_ramas()
    for r in ramas:
        icono = '✓' if r['estado'] == 'abierta' else '✕'
        camino = []
        for n in r['nodos']:
            if n.generada_por is None:
                camino.append('raíz')
            else:
                lado = f" {n.lado}" if n.lado else ''
                camino.append(f"{n.rule} de {formula_a_string(n.generada_por)}{lado}")
        print(f"{icono} RAMA {r['numero']} [{r['estado']}]: " + " → ".join(camino))
        print("   " + ", ".join(formula_a_string(f) for f in r['formulas']))
        if r['estado'] == 'abierta':
            asignacion = t.asignacion_de_rama(r, dicc)
            partes = [f"{k}={v if v != '—' else 'libre'}" for k, v in asignacion.items()]
            print("   modelo: " + ", ".join(partes))
        elif r['cierre']:
            a, b = r['cierre']
            print(f"   cierra: {formula_a_string(a)} y {formula_a_string(b)}")
        print()

    abiertas = [r for r in ramas if r['estado'] == 'abierta']
    cerradas = [r for r in ramas if r['estado'] == 'cerrada']

    print(f"Resumen: {len(ramas)} rama(s) — {len(abiertas)} abierta(s), {len(cerradas)} cerrada(s)")

    # Verificación automática del enunciado
    errores = []
    if len(ramas) != 3:
        errores.append(f"se esperaban 3 ramas y hay {len(ramas)}")
    if len(cerradas) != 2:
        errores.append(f"se esperaban 2 ramas cerradas y hay {len(cerradas)}")
    if len(abiertas) != 1:
        errores.append(f"se esperaba 1 rama abierta y hay {len(abiertas)}")
    else:
        modelo = t.asignacion_de_rama(abiertas[0], dicc)
        esperado = {'p': 'V', 'q': 'V', 'r': 'F'}
        if modelo != esperado:
            errores.append(f"el modelo esperado era {esperado} y se obtuvo {modelo}")

    if errores:
        print("\n✗ FALLA: " + "; ".join(errores))
        return 1

    print("\n✓ El árbol coincide con el caso de prueba del enunciado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
