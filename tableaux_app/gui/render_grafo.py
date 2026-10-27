# -*- coding: utf-8 -*-
import networkx as nx
import matplotlib.pyplot as plt
from tableaux_app.core.tableau import Tableau
from tableaux_app.core.formulas import (
    Atom, Not, And, Or, Imp, Iff, formula_a_string,
)


def _letras_de(f, acc):
    """Recorre una fórmula y acumula los id de sus átomos en orden de aparición."""
    if isinstance(f, Atom):
        acc.append(f.id)
    elif isinstance(f, Not):
        _letras_de(f.f, acc)
    elif isinstance(f, (And, Or, Imp, Iff)):
        _letras_de(f.left, acc)
        _letras_de(f.right, acc)


def _modelo_texto(rama, formulas_iniciales):
    """Modelo parcial de una rama como texto: p=V, q=F, r=libre."""
    letras = []
    for f in formulas_iniciales:
        _letras_de(f, letras)
    vistas = []
    for letra in letras:
        if letra not in vistas:
            vistas.append(letra)

    partes = []
    for letra in vistas:
        valor = 'libre'
        for f in rama['formulas']:
            if isinstance(f, Atom) and f.id == letra:
                valor = 'V'
                break
            if isinstance(f, Not) and isinstance(f.f, Atom) and f.f.id == letra:
                valor = 'F'
                break
        partes.append(f'{letra}={valor}')
    return ', '.join(partes)


def layout_arbol_jerarquico(G, root):
    """
    Layout de árbol clásico: cada hoja ocupa una columna y cada padre queda
    centrado sobre sus hijos. Así las ramas se ven como caminos separados.
    """
    profundidad = {}
    pos_x = {}
    siguiente_columna = [0]

    def recorrer(n, nivel):
        profundidad[n] = nivel
        hijos = list(G.successors(n))
        if not hijos:
            x = siguiente_columna[0]
            siguiente_columna[0] += 1
        else:
            xs = [recorrer(h, nivel + 1) for h in hijos]
            x = (min(xs) + max(xs)) / 2
        pos_x[n] = x
        return x

    recorrer(root, 0)

    max_x = max(pos_x.values()) if pos_x else 0
    max_y = max(profundidad.values()) if profundidad else 0

    pos = {}
    for n in pos_x:
        x = pos_x[n] / max_x if max_x else 0.5
        y = -profundidad[n] / max_y if max_y else 0.0
        pos[n] = (x, y)
    return pos


def etiqueta_nodo(node, parent=None, numero_rama=None, modelo=None):
    """Texto de un nodo.

    La raíz muestra TODAS las reglas iniciales. Cada hijo muestra solo lo que
    añadió su expansión (así se ve el camino de cada rama), junto con la fórmula
    y el tipo de regla (α/β) que lo generó. Las hojas llevan número de rama y,
    si están abiertas, su modelo.
    """
    lineas = []

    if parent is None:
        lineas.append('REGLAS INICIALES')
    elif node.generada_por is not None:
        tipo = node.rule or 'α'
        lado = f', rama {node.lado}' if node.lado else ''
        lineas.append(f'{tipo} de {formula_a_string(node.generada_por)}{lado}')

    if parent is None:
        nuevas = node.formulas
    else:
        nuevas = node.formulas[len(parent.formulas):]

    lineas.extend(formula_a_string(f) for f in nuevas)

    es_hoja = len(node.children) == 0
    if es_hoja and numero_rama is not None:
        lineas.insert(0, f'RAMA {numero_rama}')

    if node.status == 'closed':
        if node.closes_with:
            a, b = node.closes_with
            lineas.append(f'✕ CERRADA ({formula_a_string(a)}, {formula_a_string(b)})')
        else:
            lineas.append('✕ CERRADA')
    elif es_hoja:
        if modelo:
            lineas.append(f'✓ ABIERTA ({modelo})')
        else:
            lineas.append('✓ ABIERTA')

    return '\n'.join(lineas)


class RenderGrafo:
    def __init__(self, tableau: Tableau):
        self.tableau = tableau
        self.G = nx.DiGraph()

    def construir_grafo(self):
        self.G.clear()
        ramas = self.tableau.obtener_ramas()
        # Número de rama y modelo para etiquetar las hojas
        numero_rama = {r['hoja'].id: r['numero'] for r in ramas}
        modelo_rama = {
            r['hoja'].id: _modelo_texto(r, self.tableau.root.formulas)
            for r in ramas if r['estado'] == 'abierta'
        }

        def dfs(node, parent=None):
            label = etiqueta_nodo(node, parent, numero_rama.get(node.id),
                                  modelo_rama.get(node.id))
            self.G.add_node(node.id, label=label, status=node.status)
            if parent is not None:
                self.G.add_edge(parent.id, node.id)
            for c in node.children:
                dfs(c, node)

        dfs(self.tableau.root)
        return self.G

    def dibujar_en(self, ax, font_size=None):
        """Dibuja el árbol en un eje de matplotlib (lo usan la GUI y guardar())."""
        G = self.construir_grafo()
        ax.clear()
        if len(G.nodes()) == 0:
            return

        pos = layout_arbol_jerarquico(G, self.tableau.root.id)
        niveles = len({round(y, 6) for _, y in pos.values()})
        hojas = max(1, sum(1 for n in G.nodes() if G.out_degree(n) == 0))

        if font_size is None:
            font_size = max(6, min(11, 90 // max(hojas, niveles // 2 + 1)))

        colores = []
        for n in G.nodes():
            estado = G.nodes[n].get('status', 'open')
            if estado == 'closed':
                colores.append('#ff8787')   # rojo: rama cerrada
            elif estado == 'open':
                colores.append('#8ce99a')   # verde: rama abierta
            else:
                colores.append('#ffe066')   # amarillo: nodo interno

        # Nodos con tamaño proporcional al texto para que no se solapen
        size = 2600 if font_size >= 9 else 2000
        nx.draw_networkx_nodes(G, pos, node_color=colores, node_size=size, alpha=0.95,
                               linewidths=2, edgecolors='#212529', ax=ax)
        nx.draw_networkx_edges(G, pos, arrowstyle='-|>', arrowsize=18, width=1.8,
                               edge_color='#495057', ax=ax)
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_labels(
            G, pos, labels, font_size=font_size, font_weight='bold', ax=ax,
            bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor='none', alpha=0.75),
        )

        ax.set_title('Árbol Semántico (Tableaux) — ramas α/β', fontsize=13, fontweight='bold')
        ax.set_axis_off()
        ax.margins(x=0.12, y=0.12)

    def dibujar(self, figsize=(14, 10)):
        self.fig = plt.figure(figsize=figsize)
        ax = self.fig.add_subplot(111)
        self.dibujar_en(ax)
        plt.tight_layout()
        plt.show()

    def guardar(self, filename: str, figsize=None):
        G = self.construir_grafo()
        if len(G.nodes()) == 0:
            return filename
        # El lienzo crece con el árbol para que quepa todo
        if figsize is None:
            hojas = max(1, sum(1 for n in G.nodes() if G.out_degree(n) == 0))
            alto = max(8, 2.2 * (len(G.nodes()) ** 0.55))
            ancho = max(9, 2.6 * hojas ** 0.8)
            figsize = (min(ancho, 40), min(alto, 40))
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111)
        self.dibujar_en(ax)
        fig.tight_layout()
        fig.savefig(filename, dpi=180, bbox_inches='tight')
        plt.close(fig)
        return filename
