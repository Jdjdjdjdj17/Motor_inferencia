# -*- coding: utf-8 -*-
"""Ventanas auxiliares de la aplicación.

- VentanaReglas: lista las reglas del último análisis y permite eliminarlas del texto.
- VentanaAtomos: lista los átomos en uso y en qué reglas aparece cada uno.

Las dos se actualizan solas cada vez que la aplicación vuelve a analizar el texto
(App._refrescar_ventanas). Un átomo existe mientras alguna regla lo use; cuando se
elimina la última regla que lo usaba, desaparece de la lista.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from tableaux_app.core.formulas import Atom, Not, formula_a_string
from tableaux_app.core.parser import quitar_frases
from tableaux_app.gui.explicar import formula_en_palabras


def atomos_de(f, acumulado=None):
    """Conjunto con las letras de los átomos que aparecen en una fórmula."""
    if acumulado is None:
        acumulado = set()
    if isinstance(f, Atom):
        acumulado.add(f.id)
    elif isinstance(f, Not):
        atomos_de(f.f, acumulado)
    else:
        for hijo in (getattr(f, 'left', None), getattr(f, 'right', None)):
            if hijo is not None:
                atomos_de(hijo, acumulado)
    return acumulado


def _cantidad(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def _tabla_con_scroll(padre, columnas, **opciones):
    """Treeview con barra de desplazamiento. `columnas` = [(id, título, ancho, estirar)]."""
    marco = ttk.Frame(padre)
    marco.pack(fill=tk.BOTH, expand=True, padx=8)
    tabla = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings", **opciones)
    for ident, titulo, ancho, estirar in columnas:
        tabla.heading(ident, text=titulo)
        tabla.column(ident, width=ancho, minwidth=40, stretch=estirar,
                     anchor=tk.CENTER if ancho <= 70 else tk.W)
    barra = ttk.Scrollbar(marco, orient=tk.VERTICAL, command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    barra.pack(side=tk.RIGHT, fill=tk.Y)
    return tabla


class VentanaReglas(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("Reglas")
        self.geometry("920x480")
        self.minsize(620, 320)

        self.resumen = tk.StringVar()
        ttk.Label(self, textvariable=self.resumen).pack(anchor=tk.W, padx=8, pady=(8, 4))

        self.tabla = _tabla_con_scroll(
            self,
            [("n", "N°", 55, False), ("formula", "Fórmula", 230, False), ("texto", "Texto", 600, True)],
            selectmode="extended",
        )
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)
        self.tabla.bind("<Delete>", lambda _e: self.eliminar())

        self.detalle = tk.StringVar()
        ttk.Label(self, textvariable=self.detalle, wraplength=880, justify=tk.LEFT
                  ).pack(fill=tk.X, padx=8, pady=6)

        botones = ttk.Frame(self)
        botones.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(botones, text="Eliminar seleccionadas", command=self.eliminar).pack(side=tk.LEFT)
        ttk.Label(botones, text="   Ctrl+Z en el cuadro de texto principal deshace la eliminación."
                  ).pack(side=tk.LEFT)
        ttk.Button(botones, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT)

        self.refrescar()

    def refrescar(self):
        """Vuelve a llenar la lista con las reglas del último análisis."""
        app = self.app
        self.tabla.delete(*self.tabla.get_children())
        for i, f in enumerate(app.formulas):
            frase = app.fuentes[i][1] if i < len(app.fuentes) else ""
            self.tabla.insert("", tk.END, iid=str(i),
                              values=(f"R{i + 1}", formula_a_string(f), frase))
        n = len(app.formulas)
        if n:
            self.resumen.set(
                f"{_cantidad(n, 'regla', 'reglas')}. Selecciona una o varias y pulsa "
                "«Eliminar» (o la tecla Supr)."
            )
        else:
            self.resumen.set("No hay reglas. Escribe un texto y pulsa «Generar Árbol».")
        self.detalle.set("")

    def _al_seleccionar(self, _evento=None):
        seleccion = self.tabla.selection()
        if not seleccion:
            self.detalle.set("")
            return
        if len(seleccion) > 1:
            self.detalle.set(f"{_cantidad(len(seleccion), 'regla seleccionada', 'reglas seleccionadas')}.")
            return
        i = int(seleccion[0])
        f = self.app.formulas[i]
        usados = atomos_de(f)
        letras = [a for a in (self.app.dicc.atomos if self.app.dicc else []) if a in usados]
        self.detalle.set(
            f"Se lee: {formula_en_palabras(f, self.app.dicc)}\n"
            f"Átomos que usa: {', '.join(letras) if letras else '—'}"
        )

    def eliminar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Reglas", "Selecciona una o varias reglas para eliminar.", parent=self)
            return
        indices = [int(i) for i in seleccion]
        frases = sorted({self.app.fuentes[i][0] for i in indices if i < len(self.app.fuentes)})
        total = sum(1 for n, _ in self.app.fuentes if n in set(frases))
        mensaje = f"Se eliminará{'n' if len(indices) != 1 else ''} del texto {_cantidad(len(indices), 'regla', 'reglas')}."
        if total > len(indices):
            mensaje += (
                "\n\nOjo: algunas frases contienen varias reglas y se quitan completas "
                f"({_cantidad(total, 'regla', 'reglas')} en total)."
            )
        mensaje += "\n\nLos átomos que solo usaban estas reglas también desaparecen."
        if not messagebox.askyesno("Eliminar reglas", mensaje, parent=self):
            return
        self.app.eliminar_frases(frases)


class VentanaAtomos(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("Átomos")
        self.geometry("760x420")
        self.minsize(520, 280)

        self.resumen = tk.StringVar()
        ttk.Label(self, textvariable=self.resumen).pack(anchor=tk.W, padx=8, pady=(8, 4))

        self.tabla = _tabla_con_scroll(
            self,
            [("letra", "Letra", 60, False), ("significado", "Significado", 340, True),
             ("usado", "Usado en", 300, True)],
            selectmode="browse",
        )

        botones = ttk.Frame(self)
        botones.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(botones, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT)

        self.refrescar()

    def refrescar(self):
        """Vuelve a llenar la tabla con los átomos que alguna regla está usando."""
        app = self.app
        self.tabla.delete(*self.tabla.get_children())
        usos = {}
        for i, f in enumerate(app.formulas):
            for letra in atomos_de(f):
                usos.setdefault(letra, []).append(i + 1)
        atomos = app.dicc.tabla() if app.dicc else []
        for info in atomos:
            reglas = usos.get(info.id, [])
            lista = ", ".join(f"R{k}" for k in reglas[:12])
            if len(reglas) > 12:
                lista += f" y {len(reglas) - 12} más"
            self.tabla.insert("", tk.END, iid=info.id, values=(
                info.id, info.texto, f"{_cantidad(len(reglas), 'regla', 'reglas')}: {lista}"
            ))
        if atomos:
            self.resumen.set(
                f"{_cantidad(len(atomos), 'átomo', 'átomos')} en uso. "
                "Un átomo desaparece cuando se elimina la última regla que lo usa."
            )
        else:
            self.resumen.set("No hay átomos. Escribe un texto y pulsa «Generar Árbol».")


class ControlVentanasMixin:
    """Lo que la App necesita para manejar las ventanas de reglas y átomos y eliminar reglas.

    La App debe tener: root, text_input, dicc, texto_reglas(), guardar_sesion() y
    generar(silencioso, conservar_letras). Aquí se crean formulas, fuentes y _texto_analizado,
    que generar() actualiza en cada análisis.
    """

    def _iniciar_ventanas(self):
        self.formulas = []  # reglas del último análisis
        self.fuentes = []  # (n° de frase, frase) de cada regla, en el mismo orden
        self._texto_analizado = None  # texto exacto que se analizó
        self._ventana_reglas = None
        self._ventana_atomos = None

    def _abrir_ventana(self, atributo, clase):
        ventana = getattr(self, atributo)
        if ventana is not None and ventana.winfo_exists():
            ventana.deiconify()
            ventana.lift()
            ventana.focus_force()
            return
        setattr(self, atributo, clase(self.root, self))

    def ver_reglas(self):
        self._abrir_ventana('_ventana_reglas', VentanaReglas)

    def ver_atomos(self):
        self._abrir_ventana('_ventana_atomos', VentanaAtomos)

    def _refrescar_ventanas(self):
        for ventana in (self._ventana_reglas, self._ventana_atomos):
            if ventana is not None and ventana.winfo_exists():
                ventana.refrescar()

    def eliminar_frases(self, numeros):
        """Quita del texto las frases con esos números (los del último análisis) y recalcula todo.
        Los átomos que solo usaban esas frases desaparecen; los demás conservan su letra."""
        texto = self.texto_reglas()
        if texto != self._texto_analizado:
            messagebox.showinfo(
                "Reglas",
                "El texto cambió desde el último análisis.\n"
                "Pulsa «Generar Árbol» y vuelve a intentarlo.",
            )
            return False
        nuevo = quitar_frases(texto, numeros)
        # replace es una sola operación: un único Ctrl+Z deshace la eliminación completa
        self.text_input.replace('1.0', 'end-1c', nuevo)
        self.guardar_sesion()
        self.generar(silencioso=True, conservar_letras=True)
        return True
