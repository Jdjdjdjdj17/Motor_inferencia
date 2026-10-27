# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from tableaux_app.core.parser import texto_a_formulas
from tableaux_app.core.errores import ErrorSintaxis
from tableaux_app.core.tableau import Tableau
from tableaux_app.core.formulas import formula_a_string
from tableaux_app.gui.gestor_reglas import GestorReglas
from tableaux_app.gui.render_grafo import RenderGrafo
from tableaux_app.gui.explicar import (
    formula_y_lectura, modelo_dict_en_palabras, modelo_en_palabras,
    pasos_de_rama, resultado_de_rama, tabla_de_atomos,
    valores_de_modelo, valores_de_rama,
)
from tableaux_app.utils.sesion import (
    cargar_ultima_sesion, cargar_ultima_sesion_nombre, guardar_ultima_sesion,
    cargar_archivo_reglas, guardar_archivo_reglas,
)


def _cantidad(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


TEXTO_EJEMPLO = (
    "Si es de día, entonces voy a trabajar.\n"
    "Si llueve, entonces no voy a trabajar.\n"
    "Es de día."
)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Tableaux - Árbol Semántico")
        self.root.geometry("1400x900")
        
        # Frame superior
        top_frame = ttk.Frame(root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Reglas en lenguaje natural:").pack(anchor=tk.W)
        
        self.text_input = scrolledtext.ScrolledText(top_frame, height=8, wrap=tk.WORD)
        self.text_input.pack(fill=tk.X)
        texto_guardado = cargar_ultima_sesion()
        if texto_guardado is None:
            texto_guardado = TEXTO_EJEMPLO
        self.text_input.insert(tk.END, texto_guardado)

        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Generar Árbol", command=self.generar).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Limpiar", command=self.limpiar).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Guardar Imagen", command=self.guardar).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Guardar reglas", command=self.guardar_reglas).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Abrir reglas", command=self.abrir_reglas).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Administrar reglas", command=self.administrar_reglas).pack(side=tk.LEFT)
        
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

        # Pestaña 2: todas las ramas
        tab_ramas = ttk.Frame(cuaderno)
        cuaderno.add(tab_ramas, text="Ramas")
        self.text_ramas = scrolledtext.ScrolledText(tab_ramas, height=20, wrap=tk.WORD)
        self.text_ramas.pack(fill=tk.BOTH, expand=True)

        # Pestaña 3: modelos (ramas abiertas)
        tab_modelos = ttk.Frame(cuaderno)
        cuaderno.add(tab_modelos, text="Modelos")
        self.text_modelos = scrolledtext.ScrolledText(tab_modelos, height=20, wrap=tk.WORD)
        self.text_modelos.pack(fill=tk.BOTH, expand=True)

        self.cuaderno = cuaderno
        
        # Derecha - grafo
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="Árbol Semántico (Grafo)").pack(anchor=tk.W)
        self.fig = Figure(figsize=(8,6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.dicc = None
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
            formulas, _ = texto_a_formulas(texto)
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
        self.text_input.delete('1.0', tk.END)
        self.text_info.delete('1.0', tk.END)
        self.text_ramas.delete('1.0', tk.END)
        self.text_modelos.delete('1.0', tk.END)
        self.ax.clear()
        self.canvas.draw()
        self.tableau = None
        self.nombre_reglas_actual = ""
        self.guardar_sesion()

    def generar(self, silencioso=False):
        try:
            texto = self.texto_reglas()
            self.guardar_sesion()
            formulas, dicc = texto_a_formulas(texto)
            if not formulas:
                if not silencioso:
                    messagebox.showwarning("Aviso", "Escribe al menos una regla.")
                return
            self.dicc = dicc
            # Crear tableau
            self.tableau = Tableau(formulas)
            self.tableau.expandir()
            self.mostrar_info(formulas, dicc)
            self.mostrar_ramas()
            self.mostrar_modelos()
            self.dibujar_grafo()
        except ErrorSintaxis as e:
            if not silencioso:
                messagebox.showwarning("No pude entender las reglas", str(e))
        except Exception as e:
            if not silencioso:
                messagebox.showerror("Error", str(e))
            import traceback
            traceback.print_exc()
    
    def _camino_de_rama(self, rama):
        """Pasos del camino raíz→hoja, explicados con los átomos."""
        return pasos_de_rama(rama, self.tableau, self.dicc)

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

        # Caminos posibles: las ramas que no se contradicen
        self.text_info.insert(tk.END, "\n=== CAMINO CORRECTO ===\n")
        if not self.tableau:
            self.text_info.insert(tk.END, "(genera el árbol para verlo)\n")
            return
        abiertas = [r for r in self.tableau.obtener_ramas() if r['estado'] == 'abierta']
        if not abiertas:
            self.text_info.insert(
                tk.END,
                "No hay ningún camino posible: las reglas se contradicen.\n"
            )
            return
        for r in abiertas:
            self.text_info.insert(tk.END, f"✓ Rama {r['numero']}\n")
            self.text_info.insert(tk.END, "   Cómo se desarrolló:\n")
            for i, paso in enumerate(self._camino_de_rama(r), start=1):
                self.text_info.insert(tk.END, f"     {i}. {paso}\n")
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
    
    def mostrar_ramas(self):
        """Lista TODAS las ramas del árbol, posibles y descartadas, en palabras."""
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
        self.text_ramas.insert(
            tk.END, "Átomos: " + tabla_de_atomos(self.dicc) + "\n"
        )
        self.text_ramas.insert(tk.END, "=" * 46 + "\n")

        for r in ramas:
            es_posible = r['estado'] == 'abierta'
            icono = '✓' if es_posible else '✕'
            etiqueta = 'POSIBLE' if es_posible else 'SE DESCARTA'
            self.text_ramas.insert(
                tk.END, f"\n{icono} RAMA {r['numero']} — {etiqueta}\n"
            )

            self.text_ramas.insert(tk.END, "   Cómo se desarrolló:\n")
            for i, paso in enumerate(pasos_de_rama(r, self.tableau, self.dicc), start=1):
                self.text_ramas.insert(tk.END, f"     {i}. {paso}\n")

            self.text_ramas.insert(tk.END, "   Fórmulas acumuladas:\n")
            for f in r['formulas']:
                self.text_ramas.insert(
                    tk.END, f"     • {formula_y_lectura(f, self.dicc)}\n"
                )

            self.text_ramas.insert(
                tk.END, f"   {icono} "
                + resultado_de_rama(r, self.tableau, self.dicc) + "\n"
            )
            if es_posible:
                self.text_ramas.insert(
                    tk.END, "   " + modelo_en_palabras(r, self.tableau, self.dicc) + "\n"
                )
                self.text_ramas.insert(
                    tk.END, "   Valores: "
                    + valores_de_rama(r, self.tableau, self.dicc) + "\n"
                )

    def mostrar_modelos(self):
        self.text_modelos.delete('1.0', tk.END)
        if not self.tableau or not self.dicc:
            return
        hojas = self.tableau.obtener_hojas_abiertas()
        modelos = self.tableau.extraer_modelos(self.dicc)
        self.text_modelos.insert(tk.END, f"Ramas posibles: {len(hojas)}\n\n")
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
    
    def dibujar_grafo(self):
        self.ax.clear()
        if not self.tableau:
            self.canvas.draw()
            return
        render = RenderGrafo(self.tableau)
        render.dibujar_en(self.ax)
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
