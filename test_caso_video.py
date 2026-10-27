# -*- coding: utf-8 -*-
from tableaux_app.core.parser import texto_a_formulas
from tableaux_app.core.tableau import Tableau
from tableaux_app.core.formulas import formula_a_string

texto = """Si es de día, entonces voy a trabajar.
Si llueve, entonces no voy a trabajar.
Es de día."""

formulas, dicc = texto_a_formulas(texto)
print("=== FÓRMULAS ===")
for i,f in enumerate(formulas):
    print(f"R{i+1}: {formula_a_string(f)}")
print("\n=== TABLA DE ÁTOMOS ===")
for info in dicc.tabla():
    print(f"{info.id}: {info.texto}")
print("\n=== TABLEAU ===")
t = Tableau(formulas)
t.expandir()
hojas = t.obtener_hojas_abiertas()
modelos = t.extraer_modelos(dicc)
print(f"Ramas abiertas: {len(hojas)}")
if len(hojas) == 0:
    print("BASE DE CONOCIMIENTO INCONSISTENTE")
else:
    for i,m in enumerate(modelos):
        partes = []
        for letra in m:
            v = m[letra]
            if v == '—': partes.append(f"{letra}=libre")
            else: partes.append(f"{letra}={v}")
        print(f"Modelo {i+1}: " + ", ".join(partes))
