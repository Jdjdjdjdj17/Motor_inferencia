# -*- coding: utf-8 -*-
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from tableaux_app.core.tableau import Tableau
from tableaux_app.core.formulas import formula_a_string

# El dibujo se calcula en "unidades" = píxeles con una letra de tamaño FUENTE_BASE.
# Cada bloque ocupa el espacio que realmente necesita su texto y se deja un hueco entre bloques,
# así que nunca se encima uno con otro, a ningún zoom (el zoom escala texto y espacio por igual).
FUENTE_BASE = 10
HUECO_X = 30   # espacio mínimo entre bloques vecinos (unidades)
HUECO_Y = 60   # espacio entre niveles (unidades)
MARGEN = 40
MAX_PIXELES_IMAGEN = 6000  # tope del lado mayor al guardar una imagen


def etiqueta_nodo(node, parent=None, numero_rama=None):
    """Texto de un nodo, solo con lo que agrega ese paso (sin acumular).

    - Raíz: las reglas iniciales completas.
    - Cada hijo: solo las fórmulas nuevas que agrega su expansión.
    - Hoja: su número de rama y un ✓ si está abierta o una ✕ si está cerrada.
      El color del bloque (verde/rojo) refuerza el estado sin escribir palabras.
    """
    lineas = []
    es_hoja = len(node.children) == 0

    if parent is None:
        lineas.append('REGLAS INICIALES')
        lineas.extend(formula_a_string(f) for f in node.formulas)
    else:
        nuevas = node.formulas[len(parent.formulas):]
        lineas.extend(formula_a_string(f) for f in nuevas)

    if es_hoja and numero_rama is not None and parent is not None:
        lineas.insert(0, f'RAMA {numero_rama}')

    if node.status == 'closed':
        lineas.append('✕')
    elif es_hoja:
        lineas.append('✓')

    return '\n'.join(lineas)


# Por encima de este número de nodos el árbol ya no se dibuja (no se podría leer).
# Los resultados siguen en las pestañas Reglas, Ramas, Explicación y Modelos.
LIMITE_DIBUJO = 250


def _aviso_arbol_grande(ax, nodos):
    ax.clear()
    ax.text(
        0.5, 0.5,
        f"El árbol tiene {nodos} nodos: es demasiado grande para dibujarlo.\n\n"
        "Los resultados completos están en las pestañas\n"
        "Reglas y átomos, Ramas, Explicación y Modelos.",
        ha='center', va='center', fontsize=12, transform=ax.transAxes,
    )
    ax.set_axis_off()


class RenderGrafo:
    def __init__(self, tableau: Tableau):
        self.tableau = tableau
        self.G = nx.DiGraph()
        # Los llena dibujar_en(); los usa VistaArbol (zoom) y guardar()
        self.limites = None   # (x0, x1, y0, y1) del dibujo, en unidades
        self.textos = []      # los bloques de texto (artistas de matplotlib)
        self.fuente_base = FUENTE_BASE
        self.dpi_medida = None  # DPI de la figura cuando se midieron los bloques

    def construir_grafo(self):
        self.G.clear()
        ramas = self.tableau.obtener_ramas()
        # Número de rama para etiquetar las hojas
        numero_rama = {r['hoja'].id: r['numero'] for r in ramas}

        def dfs(node, parent=None):
            label = etiqueta_nodo(node, parent, numero_rama.get(node.id))
            self.G.add_node(node.id, label=label, status=node.status)
            if parent is not None:
                self.G.add_edge(parent.id, node.id)
            for c in node.children:
                dfs(c, node)

        dfs(self.tableau.root)
        return self.G

    # ---------- medida y posición de los bloques ----------
    def _medir(self, ax, etiquetas):
        """Ancho y alto real (en unidades) de cada bloque, con su relleno."""
        fig = ax.figure
        renderer = fig.canvas.get_renderer()
        relleno = 0.45 * FUENTE_BASE * fig.dpi / 72.0
        tam = {}
        for n, texto in etiquetas.items():
            t = ax.text(0, 0, texto, fontsize=FUENTE_BASE, fontweight='bold')
            caja = t.get_window_extent(renderer)
            t.remove()
            tam[n] = (caja.width + 2 * relleno, caja.height + 2 * relleno)
        return tam

    def _colocar(self, G, tam):
        """Posición (x, y) de cada bloque. A cada nodo se le reserva un tramo horizontal tan ancho
        como lo que necesitan sus hijos (o él mismo, si es más ancho): los tramos de nodos
        distintos nunca se cruzan, así que los bloques no se encimen."""
        raiz = self.tableau.root.id
        hijos = {n: list(G.successors(n)) for n in G.nodes()}

        ancho_tramo = {}

        def calcular(n):
            suma = 0.0
            for h in hijos[n]:
                suma += calcular(h)
            ancho_tramo[n] = max(tam[n][0] + HUECO_X, suma)
            return ancho_tramo[n]

        xs = {}

        def colocar(n, izq):
            total = ancho_tramo[n]
            hs = hijos[n]
            if not hs:
                xs[n] = izq + total / 2
                return
            suma = sum(ancho_tramo[h] for h in hs)
            cursor = izq + (total - suma) / 2
            centros = []
            for h in hs:
                colocar(h, cursor)
                centros.append(xs[h])
                cursor += ancho_tramo[h]
            medio = (min(centros) + max(centros)) / 2
            # centrado sobre sus hijos, sin salirse de su propio tramo
            minimo = izq + tam[n][0] / 2
            maximo = izq + total - tam[n][0] / 2
            xs[n] = min(max(medio, minimo), maximo)

        calcular(raiz)
        colocar(raiz, 0.0)

        # Niveles: cada uno tan alto como su bloque más alto
        profundidad = {raiz: 0}
        orden = [raiz]
        for n in orden:
            for h in hijos[n]:
                profundidad[h] = profundidad[n] + 1
                orden.append(h)
        alto_nivel = {}
        for n, d in profundidad.items():
            alto_nivel[d] = max(alto_nivel.get(d, 0.0), tam[n][1])
        y_nivel = {}
        acumulado = 0.0
        for d in range(len(alto_nivel)):
            y_nivel[d] = -(acumulado + alto_nivel[d] / 2)
            acumulado += alto_nivel[d] + HUECO_Y

        pos = {n: (xs[n], y_nivel[profundidad[n]]) for n in xs}
        x0 = min(xs[n] - tam[n][0] / 2 for n in xs) - MARGEN
        x1 = max(xs[n] + tam[n][0] / 2 for n in xs) + MARGEN
        y1 = alto_nivel[0] / 2 + MARGEN
        y0 = min(pos[n][1] - tam[n][1] / 2 for n in pos) - MARGEN
        return pos, (x0, x1, y0, y1)

    def dibujar_en(self, ax):
        """Dibuja el árbol en un eje de matplotlib (lo usan la GUI y guardar()).
        Devuelve True si dibujó el árbol (False si era demasiado grande o estaba vacío).
        Deja en self.limites / self.textos / self.fuente_base lo que necesita VistaArbol."""
        if len(self.tableau.nodes) > LIMITE_DIBUJO:
            _aviso_arbol_grande(ax, len(self.tableau.nodes))
            return False
        G = self.construir_grafo()
        ax.clear()
        if len(G.nodes()) == 0:
            return False

        etiquetas = nx.get_node_attributes(G, 'label')
        tam = self._medir(ax, etiquetas)
        self.dpi_medida = ax.figure.dpi
        pos, self.limites = self._colocar(G, tam)

        # Color y borde del bloque según el estado del nodo
        colores = {}
        bordes = {}
        for n in G.nodes():
            if G.nodes[n].get('status') == 'closed':
                colores[n] = '#ffa8a8'      # rojo: rama cerrada
                bordes[n] = '#c92a2a'
            elif G.out_degree(n) == 0:
                colores[n] = '#b2f2bb'      # verde: rama abierta
                bordes[n] = '#2b8a3e'
            else:
                colores[n] = '#fff3bf'      # amarillo: nodo interno
                bordes[n] = '#212529'

        # Líneas entre padre e hijo (quedan debajo de los bloques)
        segmentos = [(pos[a], pos[b]) for a, b in G.edges()]
        ax.add_collection(LineCollection(segmentos, colors='#495057', linewidths=1.6, zorder=1))

        self.textos = []
        for n, (x, y) in pos.items():
            t = ax.text(
                x, y, etiquetas[n], fontsize=FUENTE_BASE, fontweight='bold',
                ha='center', va='center', zorder=3, clip_on=True,
                bbox=dict(boxstyle='round,pad=0.45', facecolor=colores[n],
                          edgecolor=bordes[n], linewidth=1.5),
            )
            self.textos.append(t)
        self.fuente_base = FUENTE_BASE

        x0, x1, y0, y1 = self.limites
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_axis_off()
        return True

    # ---------- imagen / ventana aparte ----------
    def _figura_a_medida(self, dpi=100):
        """Figura cuyo tamaño en píxeles es el del dibujo (con tope): se ve todo y nada se encima."""
        fig = plt.figure(figsize=(8, 6), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1])
        if not self.dibujar_en(ax):
            return fig, False
        x0, x1, y0, y1 = self.limites
        ancho, alto = x1 - x0, y1 - y0
        escala = min(1.0, MAX_PIXELES_IMAGEN / max(ancho, alto))
        fig.set_size_inches(ancho * escala / dpi, alto * escala / dpi)
        for t in self.textos:
            t.set_fontsize(self.fuente_base * escala)
        return fig, True

    def dibujar(self, figsize=None):
        fig, _ = self._figura_a_medida()
        plt.show()

    def guardar(self, filename: str, figsize=None):
        if len(self.tableau.nodes) > LIMITE_DIBUJO:
            fig = plt.figure(figsize=(8, 4))
            _aviso_arbol_grande(fig.add_subplot(111), len(self.tableau.nodes))
            fig.savefig(filename, dpi=120, bbox_inches='tight')
            plt.close(fig)
            return filename
        fig, dibujado = self._figura_a_medida()
        if dibujado:
            fig.savefig(filename, dpi=100)
        plt.close(fig)
        return filename
