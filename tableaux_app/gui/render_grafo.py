# -*- coding: utf-8 -*-
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict, deque
from tableaux_app.core.tableau import Tableau
from tableaux_app.core.formulas import formula_a_string


def layout_arbol_jerarquico(G, root):
    """
    Layout jerárquico de arriba hacia abajo (tipo árbol de tableaux).
    """
    # Obtener niveles por BFS
    niveles = {}
    padre = {}
    cola = deque([root])
    padre[root] = None
    orden_bfs = []
    while cola:
        actual = cola.popleft()
        orden_bfs.append(actual)
        for hijo in G.successors(actual):
            if hijo not in padre:
                padre[hijo] = actual
                cola.append(hijo)
    
    # Calcular nivel
    for nodo in orden_bfs:
        if padre[nodo] is None:
            niveles[nodo] = 0
        else:
            niveles[nodo] = niveles[padre[nodo]] + 1
    
    # Agrupar por nivel
    por_nivel = defaultdict(list)
    for nodo, nivel in niveles.items():
        por_nivel[nivel].append(nodo)
    
    pos = {}
    max_nivel = max(por_nivel.keys()) if por_nivel else 0
    for nivel in range(max_nivel + 1):
        nodos_nivel = por_nivel[nivel]
        # Ordenar para mantener estructura coherente
        nodos_nivel = sorted(nodos_nivel)
        n = len(nodos_nivel)
        # Espaciado horizontal
        if n == 1:
            xs = [0.5]
        else:
            xs = [i / (n - 1) for i in range(n)]
        for i, nodo in enumerate(nodos_nivel):
            pos[nodo] = (xs[i], 1.0 - nivel / max(1, max_nivel))
    return pos


class RenderGrafo:
    def __init__(self, tableau: Tableau):
        self.tableau = tableau
        self.G = nx.DiGraph()
    
    def construir_grafo(self):
        self.G.clear()
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
            self.G.add_node(node.id, label=label, status=node.status)
            if parent is not None:
                self.G.add_edge(parent, node.id)
            for c in node.children:
                dfs(c, node.id)
        dfs(self.tableau.root)
        return self.G
    
    def dibujar(self, figsize=(14, 10)):
        G = self.construir_grafo()
        if len(G.nodes()) == 0:
            return
        plt.figure(figsize=figsize)
        pos = layout_arbol_jerarquico(G, self.tableau.root.id)
        node_colors = []
        for n in G.nodes():
            status = G.nodes[n].get('status', 'open')
            if status == 'closed':
                node_colors.append('#ff6b6b')
            elif status == 'open':
                node_colors.append('#51cf66')
            else:
                node_colors.append('#ffd43b')
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=4000, alpha=0.95, 
                               linewidths=2, edgecolors='black')
        nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=25, width=2, edge_color='#495057')
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_labels(G, pos, labels, font_size=7, font_weight='bold')
        plt.title('Árbol Semántico (Tableaux) - Ramificaciones α/β', fontsize=14, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.show()
    
    def guardar(self, filename: str, figsize=(16, 12)):
        G = self.construir_grafo()
        if len(G.nodes()) == 0:
            return filename
        plt.figure(figsize=figsize)
        pos = layout_arbol_jerarquico(G, self.tableau.root.id)
        node_colors = []
        for n in G.nodes():
            status = G.nodes[n].get('status', 'open')
            if status == 'closed':
                node_colors.append('#ff6b6b')
            elif status == 'open':
                node_colors.append('#51cf66')
            else:
                node_colors.append('#ffd43b')
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=4500, alpha=0.95,
                               linewidths=2, edgecolors='black')
        nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=25, width=2, edge_color='#495057')
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_labels(G, pos, labels, font_size=6, font_weight='bold')
        plt.title('Árbol Semántico (Tableaux) - Ramificaciones α/β', fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(filename, dpi=200, bbox_inches='tight')
        plt.close()
        return filename
