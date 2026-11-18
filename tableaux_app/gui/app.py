# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from tableaux_app.core.parser import texto_a_formulas
from tableaux_app.core.errores import ErrorSintaxis, ArbolDemasiadoGrande
from tableaux_app.core.atomos import DiccionarioAtomos
from tableaux_app.core.tableau import Tableau
from tableaux_app.core.formulas import formula_a_string
from tableaux_app.gui.gestor_reglas import GestorReglas
from tableaux_app.gui.render_grafo import RenderGrafo
from tableaux_app.gui.ventanas import ControlVentanasMixin
from tableaux_app.gui.explicar import (
    formula_y_lectura, modelo_dict_en_palabras, modelo_en_palabras,
    pasos_de_rama, resultado_de_rama, tabla_de_atomos,
    valores_de_modelo, valores_de_rama,
)
from tableaux_app.utils.sesion import (
    cargar_ultima_sesion, cargar_ultima_sesion_nombre, guardar_ultima_sesion,
    cargar_archivo_reglas, guardar_archivo_reglas,
)


# Con textos grandes las pestañas solo escriben un resumen (el cálculo sí usa todo).
LIMITE_RAMAS_TEXTO = 100
LIMITE_OMITIDAS_TEXTO = 100


def _cantidad(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


TEXTO_EJEMPLO = (
    "Si es de día, entonces voy a trabajar.\n"
    "Si llueve, entonces no voy a trabajar.\n"
    "Es de día."
)


class App(ControlVentanasMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("Tableaux - Árbol Semántico")
        self.root.geometry("1400x900")
        
        # Frame superior
        top_frame = ttk.Frame(root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Reglas en lenguaje natural:").pack(anchor=tk.W)
        
        self.text_input = scrolledtext.ScrolledText(top_frame, height=8, wrap=tk.WORD, undo=True)
        self.text_input.pack(fill=tk.X)
        texto_guardado = cargar_ultima_sesion()
        if texto_guardado is None:
            texto_guardado = TEXTO_EJEMPLO
        self.text_input.insert(tk.END, texto_guardado)
        self.text_input.edit_reset()  # el texto inicial no entra en el historial de Ctrl+Z

        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Generar Árbol", command=self.generar).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Limpiar", command=self.limpiar).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Guardar Imagen", command=self.guardar).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Guardar reglas", command=self.guardar_reglas).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Abrir reglas", command=self.abrir_reglas).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Administrar reglas", command=self.administrar_reglas).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Ver reglas", command=self.ver_reglas).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Ver átomos", command=self.ver_atomos).pack(side=tk.LEFT)
        
        # Paned window
        paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Izquierda
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        cuaderno = ttk.Notebook(left_frame)
        cuaderno.pack(fill=tk.BOTH, expand=True)

        # Pestaña 1: reglas y átomos
        tab_reglas = ttk.Frame(cuaderno)
        cuaderno.add(tab_reglas, text="Reglas y átomos")
        self.text_info = scrolledtext.ScrolledText(tab_reglas, height=20, wrap=tk.WORD)
        self.text_info.pack(fill=tk.BOTH, expand=True)

        # Pestaña 2: todas las ramas (detalle técnico)
        tab_ramas = ttk.Frame(cuaderno)
        cuaderno.add(tab_ramas, text="Ramas")
        self.text_ramas = scrolledtext.ScrolledText(tab_ramas, height=20, wrap=tk.WORD)
        self.text_ramas.pack(fill=tk.BOTH, expand=True)

        # Pestaña 3: explicación en palabras
        tab_explicacion = ttk.Frame(cuaderno)
        cuaderno.add(tab_explicacion, text="Explicación")
        self.text_explicacion = scrolledtext.ScrolledText(
            tab_explicacion, height=20, wrap=tk.WORD
        )
        self.text_explicacion.pack(fill=tk.BOTH, expand=True)

        # Pestaña 4: modelos (ramas posibles)
        tab_modelos = ttk.Frame(cuaderno)
        cuaderno.add(tab_modelos, text="Modelos")
        self.text_modelos = scrolledtext.ScrolledText(tab_modelos, height=20, wrap=tk.WORD)
        self.text_modelos.pack(fill=tk.BOTH, expand=True)

        self.cuaderno = cuaderno
        
        # Derecha - grafo
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        encabezado = ttk.Frame(right_frame)
        encabezado.pack(fill=tk.X)
        ttk.Label(encabezado, text="Árbol Semántico (Grafo)").pack(side=tk.LEFT)
        ttk.Button(encabezado, text="Ajustar", width=8, command=self.zoom_ajustar).pack(side=tk.RIGHT)
        ttk.Button(encabezado, text="Zoom −", width=8, command=lambda: self.zoom(1 / 1.25)).pack(side=tk.RIGHT)
        ttk.Button(encabezado, text="Zoom +", width=8, command=lambda: self.zoom(1.25)).pack(side=tk.RIGHT)
        ttk.Label(encabezado, text="Rueda: zoom · Arrastrar: mover   ").pack(side=tk.RIGHT)
        self.fig = Figure(figsize=(8,6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.dicc = None
        self.omitidas = []
        self._vista_inicial = None
        self._fuentes_base = []
        self._arrastre = None
        self._iniciar_ventanas()
        self.canvas.mpl_connect('scroll_event', self._on_rueda)
        self.canvas.mpl_connect('button_press_event', self._on_presionar)
        self.canvas.mpl_connect('motion_notify_event', self._on_mover)
        self.canvas.mpl_connect('button_release_event', self._on_soltar)
        self.tableau = None
        self.nombre_reglas_actual = cargar_ultima_sesion_nombre()
        self._gestor_reglas = None

        # Guardar las reglas al cerrar y recuperarlas al abrir
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self._after_generar = None
        if texto_guardado.strip():
            self._after_generar = self.root.after(200, lambda: self.generar(silencioso=True))

    # ---------- persistencia de reglas ----------
    def texto_reglas(self) -> str:
        return self.text_input.get('1.0', tk.END).rstrip('\n')

    def guardar_sesion(self):
        guardar_ultima_sesion(self.texto_reglas(), self.nombre_reglas_actual)

    def cerrar(self):
        if self._after_generar is not None:
            try:
                self.root.after_cancel(self._after_generar)
            except tk.TclError:
                pass
            self._after_generar = None
        self.guardar_sesion()
        self.root.destroy()

    def guardar_reglas(self):
        filename = filedialog.asksaveasfilename(
            title="Guardar reglas",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Texto", "*.txt"),
                       ("Todos los archivos", "*.*")],
        )
        if not filename:
            return
        try:
            guardar_archivo_reglas(filename, self.texto_reglas())
            messagebox.showinfo("Guardado", f"Reglas guardadas en {filename}")
        except OSError as e:
            messagebox.showerror("Error", f"No se pudieron guardar las reglas: {e}")

    def abrir_reglas(self):
        filename = filedialog.askopenfilename(
            title="Abrir reglas",
            filetypes=[("JSON o texto", "*.json *.txt"), ("JSON", "*.json"),
                       ("Texto", "*.txt"), ("Todos los archivos", "*.*")],
        )
        if not filename:
            return
        try:
            texto = cargar_archivo_reglas(filename)
        except (OSError, ValueError) as e:
            messagebox.showerror("Error", f"No se pudieron abrir las reglas: {e}")
            return
        self.text_input.delete('1.0', tk.END)
        self.text_input.insert('1.0', texto)
        self.nombre_reglas_actual = ""
        self.guardar_sesion()

    def administrar_reglas(self):
        if self._gestor_reglas is not None and self._gestor_reglas.winfo_exists():
            self._gestor_reglas.deiconify()
            self._gestor_reglas.lift()
            self._gestor_reglas.focus_force()
            return
        self._gestor_reglas = GestorReglas(self.root, self)

    def num_reglas_actual(self) -> int:
        texto = self.texto_reglas()
        try:
            formulas, _ = texto_a_formulas(texto, omitidas=[])
            return len(formulas)
        except ErrorSintaxis:
            return len([linea for linea in texto.splitlines() if linea.strip()])

    def cargar_reglas_guardadas(self, nombre: str, texto: str):
        self.text_input.delete('1.0', tk.END)
        self.text_input.insert('1.0', texto)
        self.nombre_reglas_actual = nombre
        self.guardar_sesion()
        self.cuaderno.select(0)
        self.generar()

    def limpiar(self):
        self.formulas, self.fuentes = [], []
        self.dicc = None
        self.omitidas = []
        self._texto_analizado = None
        self._refrescar_ventanas()
        self.text_input.delete('1.0', tk.END)
        self.text_info.delete('1.0', tk.END)
        self.text_ramas.delete('1.0', tk.END)
        self.text_explicacion.delete('1.0', tk.END)
        self.text_modelos.delete('1.0', tk.END)
        self.ax.clear()
        self.canvas.draw()
        self.tableau = None
        self.nombre_reglas_actual = ""
        self.guardar_sesion()

    def _limpiar_resultados(self):
        """Borra lo calculado antes para que no quede a la vista un resultado viejo."""
        self.tableau = None
        for caja in (self.text_ramas, self.text_explicacion, self.text_modelos):
            caja.delete('1.0', tk.END)
        self.ax.clear()
        self._vista_inicial = None
        self._fuentes_base = []
        self.canvas.draw()

    def _limitar_ramas(self, ramas, caja):
        """Con muchas ramas solo se escriben LIMITE_RAMAS_TEXTO (las posibles primero)."""
        if len(ramas) <= LIMITE_RAMAS_TEXTO:
            return ramas
        caja.insert(
            tk.END,
            f"(Hay {len(ramas)} ramas; se muestran solo {LIMITE_RAMAS_TEXTO}, las posibles primero.)\n"
        )
        return sorted(ramas, key=lambda r: r['estado'] != 'abierta')[:LIMITE_RAMAS_TEXTO]

    def generar(self, silencioso=False, conservar_letras=False):
        try:
            texto = self.texto_reglas()
            self.guardar_sesion()
            # Modo tolerante: las frases que no se entienden se omiten y se listan aparte
            self.omitidas = []
            self.fuentes = []
            dicc_inicial = None
            if conservar_letras and self.dicc is not None:
                # Tras eliminar reglas, los átomos que siguen en uso conservan su letra
                dicc_inicial = DiccionarioAtomos(
                    reservadas=self.dicc.key_a_id, siguiente=self.dicc.siguiente
                )
            formulas, dicc = texto_a_formulas(
                texto, dicc=dicc_inicial, omitidas=self.omitidas, fuentes=self.fuentes
            )
            self._texto_analizado = texto
            self.formulas = formulas
            self.dicc = dicc
            self._refrescar_ventanas()
            if not formulas:
                self._limpiar_resultados()
                self.mostrar_info(formulas, dicc)
                if not silencioso:
                    detalle = ""
                    if self.omitidas:
                        detalle = "\n\nNo pude usar estas frases:\n" + "\n".join(
                            f"• {f[:60]}: {m}" for _, f, m in self.omitidas[:5]
                        )
                    messagebox.showwarning("Aviso", "No encontré ninguna regla en el texto." + detalle)
                return
            self.dicc = dicc
            # Crear tableau
            self.tableau = Tableau(formulas)
            self.tableau.expandir()
            self.mostrar_info(formulas, dicc)
            self.mostrar_ramas()
            self.mostrar_explicacion()
            self.mostrar_modelos()
            self.dibujar_grafo()
        except ArbolDemasiadoGrande as e:
            self._limpiar_resultados()
            self.mostrar_info(formulas, dicc)
            self.cuaderno.select(0)
            if not silencioso:
                messagebox.showwarning("Árbol demasiado grande", str(e))
        except ErrorSintaxis as e:
            if not silencioso:
                messagebox.showwarning("No pude entender las reglas", str(e))
        except Exception as e:
            if not silencioso:
                messagebox.showerror("Error", str(e))
            import traceback
            traceback.print_exc()
    
    def mostrar_info(self, formulas, dicc):
        self.text_info.delete('1.0', tk.END)
        self.text_info.insert(tk.END, "=== FÓRMULAS ===\n")
        for i, f in enumerate(formulas):
            self.text_info.insert(tk.END, f"R{i+1}: {formula_y_lectura(f, dicc)}\n")
        self.text_info.insert(tk.END, "\n=== TABLA DE ÁTOMOS ===\n")
        tabla = dicc.tabla()
        if tabla:
            self.text_info.insert(tk.END, f"{'Letra':<6} {'Significado'}\n")
            self.text_info.insert(tk.END, "-"*40 + "\n")
            for info in tabla:
                self.text_info.insert(tk.END, f"{info.id:<6} {info.texto}\n")
        else:
            self.text_info.insert(tk.END, "(sin átomos)\n")

        omitidas = getattr(self, 'omitidas', [])
        if omitidas:
            self.text_info.insert(tk.END, f"\n=== FRASES QUE NO USÉ ({len(omitidas)}) ===\n")
            for n, frase, motivo in omitidas[:LIMITE_OMITIDAS_TEXTO]:
                resumen = frase if len(frase) <= 90 else frase[:89] + '…'
                self.text_info.insert(tk.END, f"#{n} «{resumen}»\n      {motivo}\n")
            if len(omitidas) > LIMITE_OMITIDAS_TEXTO:
                self.text_info.insert(
                    tk.END, f"… y {len(omitidas) - LIMITE_OMITIDAS_TEXTO} más.\n"
                )

        # Caminos posibles: las ramas que no se contradicen
        self.text_info.insert(tk.END, "\n=== CAMINO CORRECTO ===\n")
        if not self.tableau:
            self.text_info.insert(tk.END, "(no hay árbol: genera uno o reduce las reglas)\n")
            return
        abiertas = [r for r in self.tableau.obtener_ramas() if r['estado'] == 'abierta']
        if not abiertas:
            self.text_info.insert(
                tk.END,
                "No hay ningún camino posible: las reglas se contradicen.\n"
            )
            self.text_info.insert(
                tk.END,
                "\nEl paso a paso en palabras está en la pestaña «Explicación».\n"
            )
            return
        if len(abiertas) > LIMITE_RAMAS_TEXTO:
            self.text_info.insert(
                tk.END,
                f"Hay {len(abiertas)} caminos posibles; se muestran los primeros {LIMITE_RAMAS_TEXTO}.\n"
            )
        for r in abiertas[:LIMITE_RAMAS_TEXTO]:
            self.text_info.insert(tk.END, f"✓ Rama {r['numero']}\n")
            self.text_info.insert(
                tk.END,
                "   Fórmulas (referencia): "
                + ", ".join(formula_a_string(f) for f in r['formulas']) + "\n"
            )
            self.text_info.insert(
                tk.END, "   " + modelo_en_palabras(r, self.tableau, dicc) + "\n"
            )
            self.text_info.insert(
                tk.END, "   Valores: " + valores_de_rama(r, self.tableau, dicc) + "\n"
            )
        self.text_info.insert(
            tk.END,
            "\nEl paso a paso en palabras está en la pestaña «Explicación».\n"
        )
    
    def mostrar_ramas(self):
        """Detalle técnico de TODAS las ramas: camino, fórmulas y cierre/modelo."""
        self.text_ramas.delete('1.0', tk.END)
        if not self.tableau or not self.dicc:
            return
        ramas = self.tableau.obtener_ramas()
        posibles = sum(1 for r in ramas if r['estado'] == 'abierta')
        descartadas = len(ramas) - posibles
        self.text_ramas.insert(
            tk.END,
            f"{_cantidad(len(ramas), 'rama', 'ramas')}: "
            f"{_cantidad(posibles, 'posible', 'posibles')}, "
            f"{_cantidad(descartadas, 'descartada', 'descartadas')}\n"
        )
        self.text_ramas.insert(tk.END, "=" * 46 + "\n")
        ramas = self._limitar_ramas(ramas, self.text_ramas)

        for r in ramas:
            es_posible = r['estado'] == 'abierta'
            icono = '✓' if es_posible else '✕'
            etiqueta = 'POSIBLE' if es_posible else 'SE DESCARTA'
            self.text_ramas.insert(
                tk.END, f"\n{icono} RAMA {r['numero']} — {etiqueta}\n"
            )

            camino = []
            for n in r['nodos']:
                if n.generada_por is None:
                    camino.append("raíz (reglas iniciales)")
                else:
                    lado = f" ({n.lado})" if n.lado else ""
                    camino.append(
                        f"regla de {formula_a_string(n.generada_por)}{lado}"
                    )
            self.text_ramas.insert(
                tk.END, "   Camino: " + " → ".join(camino) + "\n"
            )

            self.text_ramas.insert(tk.END, "   Fórmulas acumuladas:\n")
            for f in r['formulas']:
                self.text_ramas.insert(tk.END, f"     • {formula_a_string(f)}\n")

            if es_posible:
                self.text_ramas.insert(
                    tk.END, "   ✓ Modelo: "
                    + valores_de_rama(r, self.tableau, self.dicc) + "\n"
                )
            else:
                cierre = r.get('cierre')
                if cierre:
                    a, b = cierre
                    self.text_ramas.insert(
                        tk.END,
                        f"   ✕ Se descarta: «{formula_a_string(a)}» y "
                        f"«{formula_a_string(b)}»\n"
                    )
                else:
                    self.text_ramas.insert(
                        tk.END, "   ✕ Se descarta por una contradicción\n"
                    )

    def mostrar_explicacion(self):
        """Explica cómo se formó cada rama usando el nombre de los átomos."""
        self.text_explicacion.delete('1.0', tk.END)
        if not self.tableau or not self.dicc:
            return
        ramas = self.tableau.obtener_ramas()
        posibles = sum(1 for r in ramas if r['estado'] == 'abierta')
        descartadas = len(ramas) - posibles
        self.text_explicacion.insert(tk.END, "CÓMO SE FORMARON LAS RAMAS\n")
        self.text_explicacion.insert(
            tk.END,
            f"{_cantidad(len(ramas), 'rama', 'ramas')}: "
            f"{_cantidad(posibles, 'posible', 'posibles')}, "
            f"{_cantidad(descartadas, 'descartada', 'descartadas')}\n"
        )
        self.text_explicacion.insert(
            tk.END, "Átomos: " + tabla_de_atomos(self.dicc) + "\n"
        )
        self.text_explicacion.insert(tk.END, "=" * 46 + "\n")
        ramas = self._limitar_ramas(ramas, self.text_explicacion)

        for r in ramas:
            es_posible = r['estado'] == 'abierta'
            icono = '✓' if es_posible else '✕'
            etiqueta = 'POSIBLE' if es_posible else 'SE DESCARTA'
            self.text_explicacion.insert(
                tk.END, f"\n{icono} RAMA {r['numero']} — {etiqueta}\n"
            )

            self.text_explicacion.insert(tk.END, "   Cómo se desarrolló:\n")
            for i, paso in enumerate(pasos_de_rama(r, self.tableau, self.dicc), start=1):
                self.text_explicacion.insert(tk.END, f"     {i}. {paso}\n")

            self.text_explicacion.insert(tk.END, "   Fórmulas acumuladas:\n")
            for f in r['formulas']:
                self.text_explicacion.insert(
                    tk.END, f"     • {formula_y_lectura(f, self.dicc)}\n"
                )

            self.text_explicacion.insert(
                tk.END, f"   {icono} "
                + resultado_de_rama(r, self.tableau, self.dicc) + "\n"
            )
            if es_posible:
                self.text_explicacion.insert(
                    tk.END, "   " + modelo_en_palabras(r, self.tableau, self.dicc) + "\n"
                )
                self.text_explicacion.insert(
                    tk.END, "   Valores: "
                    + valores_de_rama(r, self.tableau, self.dicc) + "\n"
                )

    def mostrar_modelos(self):
        self.text_modelos.delete('1.0', tk.END)
        if not self.tableau or not self.dicc:
            return
        hojas = self.tableau.obtener_hojas_abiertas()
        modelos = self.tableau.extraer_modelos(self.dicc, max_modelos=LIMITE_RAMAS_TEXTO)
        modo = getattr(self.tableau, 'modo', None)
        self.text_modelos.insert(
            tk.END, f"Ramas posibles: {len(hojas)}" + (f" (modo {modo})" if modo else "") + "\n"
        )
        if modo == 'compacto':
            self.text_modelos.insert(
                tk.END,
                "Modo compacto (muchas reglas): las reglas ya decididas se resuelven juntas, "
                "sin dibujar cada rama descartada. El resultado es el mismo.\n"
            )
        if len(hojas) > LIMITE_RAMAS_TEXTO:
            self.text_modelos.insert(
                tk.END, f"Se muestran los primeros {LIMITE_RAMAS_TEXTO} modelos.\n"
            )
        self.text_modelos.insert(tk.END, "\n")
        if len(hojas) == 0:
            self.text_modelos.insert(tk.END, "LAS REGLAS SE CONTRADICEN\n")
            self.text_modelos.insert(tk.END, "(No hay ningún modelo posible)\n")
            return
        for i, m in enumerate(modelos):
            self.text_modelos.insert(tk.END, f"Modelo {i+1}:\n")
            self.text_modelos.insert(
                tk.END, "  " + modelo_dict_en_palabras(m, self.dicc) + "\n"
            )
            self.text_modelos.insert(
                tk.END, "  Valores: " + valores_de_modelo(m) + "\n\n"
            )
    
    # ---------- zoom y desplazamiento del árbol ----------
    ZOOM_MIN = 0.25
    ZOOM_MAX = 12.0

    def _nivel_zoom(self):
        if not self._vista_inicial:
            return 1.0
        (x0, x1), _ = self._vista_inicial
        xa, xb = self.ax.get_xlim()
        return (x1 - x0) / (xb - xa) if xb != xa else 1.0

    def _actualizar_fuentes(self):
        """El texto de los bloques crece o se encoge junto con el zoom."""
        z = self._nivel_zoom()
        for t, base in self._fuentes_base:
            t.set_fontsize(max(2.0, base * z))

    def zoom(self, factor, centro=None):
        """factor > 1 acerca, factor < 1 aleja. `centro` = (x, y) en datos (por defecto, el centro)."""
        if not self.tableau or not self._vista_inicial:
            return
        if not (self.ZOOM_MIN <= self._nivel_zoom() * factor <= self.ZOOM_MAX):
            return
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        cx, cy = centro if centro else ((xmin + xmax) / 2, (ymin + ymax) / 2)
        self.ax.set_xlim(cx - (cx - xmin) / factor, cx + (xmax - cx) / factor)
        self.ax.set_ylim(cy - (cy - ymin) / factor, cy + (ymax - cy) / factor)
        self._actualizar_fuentes()
        self.canvas.draw_idle()

    def zoom_ajustar(self):
        """Vuelve a mostrar el árbol completo."""
        if not self._vista_inicial:
            return
        self.ax.set_xlim(*self._vista_inicial[0])
        self.ax.set_ylim(*self._vista_inicial[1])
        self._actualizar_fuentes()
        self.canvas.draw_idle()

    def _on_rueda(self, event):
        if event.inaxes is not self.ax or event.xdata is None:
            return
        self.zoom(1.2 if event.button == 'up' else 1 / 1.2, centro=(event.xdata, event.ydata))

    def _on_presionar(self, event):
        if event.inaxes is self.ax and event.button == 1 and self._vista_inicial:
            self._arrastre = (event.x, event.y, self.ax.get_xlim(), self.ax.get_ylim())

    def _on_mover(self, event):
        if not self._arrastre or event.x is None:
            return
        x0, y0, (xa, xb), (ya, yb) = self._arrastre
        dx = (event.x - x0) / self.ax.bbox.width * (xb - xa)
        dy = (event.y - y0) / self.ax.bbox.height * (yb - ya)
        self.ax.set_xlim(xa - dx, xb - dx)
        self.ax.set_ylim(ya - dy, yb - dy)
        self.canvas.draw_idle()

    def _on_soltar(self, event):
        self._arrastre = None

    def dibujar_grafo(self):
        self._vista_inicial = None
        self._fuentes_base = []
        self.ax.clear()
        if not self.tableau:
            self.canvas.draw()
            return
        render = RenderGrafo(self.tableau)
        dibujado = render.dibujar_en(self.ax)
        if dibujado:
            self._vista_inicial = (self.ax.get_xlim(), self.ax.get_ylim())
            self._fuentes_base = [(t, t.get_fontsize()) for t in self.ax.texts]
        self.canvas.draw()
    
    def guardar(self):
        if not self.tableau:
            messagebox.showwarning("Aviso", "Genera el árbol primero")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPG", "*.jpg"), ("PDF", "*.pdf")])
        if filename:
            rg = RenderGrafo(self.tableau)
            rg.guardar(filename)
            messagebox.showinfo("Guardado", f"Guardado en {filename}")

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == '__main__':
    main()
