# -*- coding: utf-8 -*-
"""Vista del árbol: zoom, desplazamiento y ajuste.

RenderGrafo calcula el dibujo en unidades = píxeles con la letra base, dejando a cada bloque
el espacio que necesita. Aquí solo se decide qué parte se ve y a qué escala `s` (píxeles de
pantalla por unidad). El texto se dibuja con tamaño fuente_base * s, así que acercar agranda
texto y bloques por igual y nunca se encimen.
"""


class VistaArbol:
    ESCALA_MIN = 0.05
    ESCALA_MAX = 3.0        # texto de hasta 30 pt
    ESCALA_LEGIBLE = 0.9    # texto de 9 pt: punto de partida cuando el árbol es muy grande
    ESCALA_AJUSTE_MIN = 0.5  # si "ver todo" deja el texto por debajo de 5 pt, se empieza más cerca
    FUENTE_MIN = 1.0

    def __init__(self, fig, ax, canvas):
        self.fig = fig
        self.ax = ax
        self.canvas = canvas
        self.render = None
        self.cx = self.cy = 0.0  # centro de la vista, en unidades del dibujo
        self.s = 1.0             # píxeles de pantalla por unidad
        self._arrastre = None
        ax.set_position([0, 0, 1, 1])  # el dibujo usa todo el lienzo
        canvas.mpl_connect('scroll_event', self._rueda)
        canvas.mpl_connect('button_press_event', self._presionar)
        canvas.mpl_connect('motion_notify_event', self._mover)
        canvas.mpl_connect('button_release_event', self._soltar)
        canvas.mpl_connect('resize_event', self._redimensionar)

    @property
    def activa(self):
        """Hay un árbol dibujado en el eje (si se limpió el eje, ya no)."""
        r = self.render
        return r is not None and bool(r.textos) and r.textos[0].axes is self.ax

    def _tam_px(self):
        return max(self.ax.bbox.width, 1.0), max(self.ax.bbox.height, 1.0)

    def _escala_ajuste(self):
        x0, x1, y0, y1 = self.render.limites
        ancho, alto = self._tam_px()
        return min(ancho / (x1 - x0), alto / (y1 - y0), 1.5)

    def _aplicar(self, fuentes=True):
        ancho, alto = self._tam_px()
        self.ax.set_xlim(self.cx - ancho / (2 * self.s), self.cx + ancho / (2 * self.s))
        self.ax.set_ylim(self.cy - alto / (2 * self.s), self.cy + alto / (2 * self.s))
        if fuentes:
            # Si el DPI de la figura cambió después de medir (pantalla con escala distinta),
            # se compensa para que el texto siga ocupando el espacio reservado.
            ajuste_dpi = (self.render.dpi_medida or self.fig.dpi) / self.fig.dpi
            tam = max(self.FUENTE_MIN, self.render.fuente_base * self.s * ajuste_dpi)
            for t in self.render.textos:
                t.set_fontsize(tam)
        self.canvas.draw_idle()

    # ---------- acciones ----------
    def mostrar(self, render):
        """Llamar justo después de render.dibujar_en(ax)."""
        self.render = render
        self._arrastre = None
        if not self.activa:
            return
        if self._escala_ajuste() >= self.ESCALA_AJUSTE_MIN:
            self.ajustar()
        else:
            # Árbol grande: se empieza con letra legible, desde arriba (la raíz).
            # El botón «Ajustar» muestra el árbol completo.
            x0, x1, y0, y1 = self.render.limites
            _, alto = self._tam_px()
            self.s = self.ESCALA_LEGIBLE
            self.cx = (x0 + x1) / 2
            self.cy = y1 - alto / (2 * self.s)
            self._aplicar()

    def ajustar(self):
        """Muestra el árbol completo."""
        if not self.activa:
            return
        x0, x1, y0, y1 = self.render.limites
        self.s = self._escala_ajuste()
        self.cx, self.cy = (x0 + x1) / 2, (y0 + y1) / 2
        self._aplicar()

    def zoom(self, factor, pantalla=None):
        """factor > 1 acerca, factor < 1 aleja. `pantalla` = (x, y) del cursor en píxeles del
        lienzo; el punto del dibujo que está bajo el cursor se queda ahí (por defecto, el centro)."""
        if not self.activa:
            return
        nuevo = min(self.ESCALA_MAX, max(self.ESCALA_MIN, self.s * factor))
        if nuevo == self.s:
            return
        ancho, alto = self._tam_px()
        if pantalla is None:
            px, py = ancho / 2, alto / 2
        else:
            px, py = pantalla[0] - self.ax.bbox.x0, pantalla[1] - self.ax.bbox.y0
        xd = self.cx + (px - ancho / 2) / self.s
        yd = self.cy + (py - alto / 2) / self.s
        self.s = nuevo
        self.cx = xd - (px - ancho / 2) / self.s
        self.cy = yd - (py - alto / 2) / self.s
        self._aplicar()

    # ---------- ratón ----------
    def _rueda(self, ev):
        if ev.inaxes is not self.ax:
            return
        self.zoom(1.2 if ev.button == 'up' else 1 / 1.2, pantalla=(ev.x, ev.y))

    def _presionar(self, ev):
        if ev.inaxes is self.ax and ev.button == 1 and self.activa:
            self._arrastre = (ev.x, ev.y, self.cx, self.cy)

    def _mover(self, ev):
        if self._arrastre is None or ev.x is None:
            return
        x0, y0, cx0, cy0 = self._arrastre
        self.cx = cx0 - (ev.x - x0) / self.s
        self.cy = cy0 - (ev.y - y0) / self.s
        self._aplicar(fuentes=False)

    def _soltar(self, ev):
        self._arrastre = None

    def _redimensionar(self, ev):
        if self.activa:
            self._aplicar()
