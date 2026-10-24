# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import networkx as nx

from tableaux_app.core.parser import texto_a_formulas
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
        
        ttk.Label(left_frame, text="Fórmulas y Tabla de Átomos").pack(anchor=tk.W)
        self.text_info = scrolledtext.ScrolledText(left_frame, height=20, wrap=tk.WORD)
        self.text_info.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(left_frame, text="Ramas Abiertas / Modelos").pack(anchor=tk.W)
        self.text_modelos = scrolledtext.ScrolledText(left_frame, height=10, wrap=tk.WORD)
        self.text_modelos.pack(fill=tk.BOTH)
        
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
        self.text_modelos.delete('1.0', tk.END)
        self.ax.clear()
        self.canvas.draw()
    
    def generar(self):
        try:
            texto = self.text_input.get('1.0', tk.END)
            formulas, dicc = texto_a_formulas(texto)
            self.dicc = dicc
            self.mostrar_info(formulas, dicc)
            # Crear tableau
            self.tableau = Tableau(formulas)
            self.tableau.expandir()
            self.mostrar_modelos()
            self.dibujar_grafo()
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
            for letra in sorted(m.keys()):
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
        from collections import defaultdict, deque
        G = nx.DiGraph()
        def dfs(node, parent=None):
            formulas_str = []
            for idx, f in enumerate(node.formulas):
                marca = '✓' if idx in node.applied else '○'
                formulas_str.append(f'{marca} {formula_a_string(f)}')
            label = '\n'.join(formulas_str)
            if node.status == 'closed':
                label += '\n✕ CERRADA'
            elif node.status == 'open' and len(node.children) == 0:
                label += '\n✓ ABIERTA'
            G.add_node(node.id, label=label, status=node.status)
            if parent is not None:
                G.add_edge(parent, node.id)
            for c in node.children:
                dfs(c, node.id)
        dfs(self.tableau.root)
        if len(G.nodes()) == 0:
            self.canvas.draw()
            return
        # Layout jerárquico
        root_id = self.tableau.root.id
        niveles = {}
        padre = {}
        cola = deque([root_id])
        padre[root_id] = None
        orden_bfs = []
        while cola:
            actual = cola.popleft()
            orden_bfs.append(actual)
            for hijo in G.successors(actual):
                if hijo not in padre:
                    padre[hijo] = actual
                    cola.append(hijo)
        for nodo in orden_bfs:
            if padre[nodo] is None:
                niveles[nodo] = 0
            else:
                niveles[nodo] = niveles[padre[nodo]] + 1
        por_nivel = defaultdict(list)
        for nodo, nivel in niveles.items():
            por_nivel[nivel].append(nodo)
        pos = {}
        max_nivel = max(por_nivel.keys()) if por_nivel else 0
        for nivel in range(max_nivel + 1):
            nodos_nivel = sorted(por_nivel[nivel])
            n = len(nodos_nivel)
            if n == 1:
                xs = [0.5]
            else:
                xs = [i / (n - 1) for i in range(n)]
            for i, nodo in enumerate(nodos_nivel):
                pos[nodo] = (xs[i], 1.0 - nivel / max(1, max_nivel))
        node_colors = []
        for n in G.nodes():
            status = G.nodes[n].get('status', 'open')
            if status == 'closed':
                node_colors.append('#ff6b6b')
            elif status == 'open':
                node_colors.append('#51cf66')
            else:
                node_colors.append('#ffd43b')
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2200, alpha=0.95, 
                               linewidths=2, edgecolors='black', ax=self.ax)
        nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=15, width=1.5, edge_color='#495057', ax=self.ax)
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_labels(G, pos, labels, font_size=5, font_weight='bold', ax=self.ax)
        self.ax.set_title('Árbol Semántico (Tableaux) - Ramificaciones α/β', fontsize=10, fontweight='bold')
        self.ax.axis('off')
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
