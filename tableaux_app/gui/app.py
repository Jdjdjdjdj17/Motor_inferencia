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
from tableaux_app.gui.render_grafo import RenderGrafo

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
        self.text_input.insert(tk.END, "Si es de día, entonces voy a trabajar.\nSi llueve, entonces no voy a trabajar.\nEs de día.")
        
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Generar Árbol", command=self.generar).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Limpiar", command=self.limpiar).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Guardar Imagen", command=self.guardar).pack(side=tk.LEFT)
        
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
    
    def limpiar(self):
        self.text_input.delete('1.0', tk.END)
        self.text_info.delete('1.0', tk.END)
        self.text_ramas.delete('1.0', tk.END)
        self.text_modelos.delete('1.0', tk.END)
        self.ax.clear()
        self.canvas.draw()

    def generar(self):
        try:
            texto = self.text_input.get('1.0', tk.END)
            formulas, dicc = texto_a_formulas(texto)
            if not formulas:
                messagebox.showwarning("Aviso", "Escribe al menos una regla.")
                return
            self.dicc = dicc
            self.mostrar_info(formulas, dicc)
            # Crear tableau
            self.tableau = Tableau(formulas)
            self.tableau.expandir()
            self.mostrar_ramas()
            self.mostrar_modelos()
            self.dibujar_grafo()
        except ErrorSintaxis as e:
            messagebox.showwarning("No pude entender las reglas", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))
            import traceback
            traceback.print_exc()
    
    def mostrar_info(self, formulas, dicc):
        self.text_info.delete('1.0', tk.END)
        self.text_info.insert(tk.END, "=== FÓRMULAS ===\n")
        for i, f in enumerate(formulas):
            self.text_info.insert(tk.END, f"R{i+1}: {formula_a_string(f)}\n")
        self.text_info.insert(tk.END, "\n=== TABLA DE ÁTOMOS ===\n")
        tabla = dicc.tabla()
        if tabla:
            self.text_info.insert(tk.END, f"{'Letra':<6} {'Significado'}\n")
            self.text_info.insert(tk.END, "-"*40 + "\n")
            for info in tabla:
                self.text_info.insert(tk.END, f"{info.id:<6} {info.texto}\n")
        else:
            self.text_info.insert(tk.END, "(sin átomos)\n")
    
    def mostrar_ramas(self):
        """Lista TODAS las ramas del árbol, abiertas y cerradas, con su camino."""
        self.text_ramas.delete('1.0', tk.END)
        if not self.tableau or not self.dicc:
            return
        ramas = self.tableau.obtener_ramas()
        abiertas = sum(1 for r in ramas if r['estado'] == 'abierta')
        cerradas = len(ramas) - abiertas
        self.text_ramas.insert(
            tk.END,
            f"{len(ramas)} rama(s): {abiertas} abierta(s), {cerradas} cerrada(s)\n"
        )
        self.text_ramas.insert(tk.END, "=" * 46 + "\n")

        for r in ramas:
            icono = '✓' if r['estado'] == 'abierta' else '✕'
            self.text_ramas.insert(tk.END, f"\n{icono} RAMA {r['numero']} — {r['estado'].upper()}\n")

            # Camino: qué paso dio cada nodo
            camino = []
            for n in r['nodos']:
                if n.generada_por is None:
                    camino.append('raíz (reglas iniciales)')
                else:
                    lado = f" {n.lado}" if n.lado else ''
                    camino.append(f"{n.rule} de {formula_a_string(n.generada_por)}{lado}")
            self.text_ramas.insert(tk.END, "   Camino: " + " → ".join(camino) + "\n")

            self.text_ramas.insert(tk.END, "   Fórmulas acumuladas:\n")
            for f in r['formulas']:
                self.text_ramas.insert(tk.END, f"     • {formula_a_string(f)}\n")

            if r['estado'] == 'cerrada':
                if r['cierre']:
                    a, b = r['cierre']
                    self.text_ramas.insert(
                        tk.END,
                        f"   ✕ Se cierra: «{formula_a_string(a)}» y «{formula_a_string(b)}»\n"
                    )
                else:
                    self.text_ramas.insert(tk.END, "   ✕ Rama cerrada\n")
            else:
                asignacion = self.tableau.asignacion_de_rama(r, self.dicc)
                partes = [f"{k}={v if v != '—' else 'libre'}" for k, v in asignacion.items()]
                self.text_ramas.insert(tk.END, "   ✓ Modelo: " + ", ".join(partes) + "\n")

    def mostrar_modelos(self):
        self.text_modelos.delete('1.0', tk.END)
        if not self.tableau or not self.dicc:
            return
        hojas = self.tableau.obtener_hojas_abiertas()
        modelos = self.tableau.extraer_modelos(self.dicc)
        self.text_modelos.insert(tk.END, f"Ramas abiertas: {len(hojas)}\n\n")
        if len(hojas) == 0:
            self.text_modelos.insert(tk.END, "BASE DE CONOCIMIENTO INCONSISTENTE\n")
            self.text_modelos.insert(tk.END, "(Todas las ramas se cierran)\n")
            return
        for i, m in enumerate(modelos):
            self.text_modelos.insert(tk.END, f"Modelo {i+1}: ")
            partes = []
            for letra in m:
                val = m[letra]
                if val == '—':
                    partes.append(f"{letra}=libre")
                else:
                    partes.append(f"{letra}={val}")
            self.text_modelos.insert(tk.END, ", ".join(partes) + "\n")
    
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
