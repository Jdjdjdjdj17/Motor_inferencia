# -*- coding: utf-8 -*-
"""Ventana para administrar los conjuntos de reglas guardados."""
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from tableaux_app.utils import sesion


class GestorReglas(tk.Toplevel):
    """Lista y administra los conjuntos de reglas guardados por el usuario."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("Administrar reglas")
        self.geometry("820x460")
        self.minsize(620, 340)
        self.transient(master)
        try:
            self.grab_set()
        except tk.TclError:
            pass

        self.nombre_var = tk.StringVar(
            value=getattr(app, "nombre_reglas_actual", "")
        )
        self._conjuntos = []
        self._crear_ui()
        self._cargar_lista()
        self.bind("<Escape>", lambda _e: self.destroy())

    # ---------- construcción de la ventana ----------
    def _crear_ui(self):
        contenedor = ttk.Frame(self, padding=10)
        contenedor.pack(fill=tk.BOTH, expand=True)

        superior = ttk.Frame(contenedor)
        superior.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(superior, text="Nombre:").pack(side=tk.LEFT)
        self.entry_nombre = ttk.Entry(superior, textvariable=self.nombre_var)
        self.entry_nombre.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 8))
        ttk.Button(
            superior, text="Guardar actual", command=self._guardar_actual
        ).pack(side=tk.LEFT)

        marco_lista = ttk.Frame(contenedor)
        marco_lista.pack(fill=tk.BOTH, expand=True)
        columnas = ("nombre", "fecha", "reglas")
        self.tree = ttk.Treeview(
            marco_lista, columns=columnas, show="headings", selectmode="browse"
        )
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("fecha", text="Última modificación")
        self.tree.heading("reglas", text="Reglas")
        self.tree.column("nombre", width=420, anchor=tk.W)
        self.tree.column("fecha", width=160, anchor=tk.CENTER)
        self.tree.column("reglas", width=80, anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra = ttk.Scrollbar(
            marco_lista, orient=tk.VERTICAL, command=self.tree.yview
        )
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=barra.set)

        inferior = ttk.Frame(contenedor)
        inferior.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(
            inferior, text="Cargar", command=self._cargar_seleccionada
        ).pack(side=tk.LEFT)
        ttk.Button(
            inferior, text="Renombrar", command=self._renombrar
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(
            inferior, text="Duplicar", command=self._duplicar
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(
            inferior, text="Eliminar", command=self._eliminar
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(
            inferior, text="Refrescar", command=self._cargar_lista
        ).pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Button(
            inferior, text="Cerrar", command=self.destroy
        ).pack(side=tk.RIGHT)

        self.estado = ttk.Label(
            contenedor, text="", foreground="#555", wraplength=780, justify=tk.LEFT
        )
        self.estado.pack(fill=tk.X, pady=(6, 0))

        self.tree.bind("<Double-1>", lambda _e: self._cargar_seleccionada())
        self.tree.bind("<Return>", lambda _e: self._cargar_seleccionada())
        self.tree.bind("<Delete>", lambda _e: self._eliminar())
        self.entry_nombre.focus_set()

    # ---------- lista ----------
    def _cargar_lista(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._conjuntos = sesion.listar_conjuntos()
        for conjunto in self._conjuntos:
            numero = conjunto.get("num_reglas")
            if not isinstance(numero, int):
                numero = len(
                    [l for l in conjunto["reglas"].splitlines() if l.strip()]
                )
            self.tree.insert(
                "", tk.END, iid=str(conjunto["ruta"]),
                values=(
                    conjunto["nombre"],
                    self._formatear_fecha(conjunto.get("modificado")),
                    numero,
                ),
            )
        self._actualizar_estado()
        if self.nombre_var.get().strip():
            self._seleccionar_por_nombre(self.nombre_var.get().strip())

    @staticmethod
    def _formatear_fecha(iso):
        if not iso:
            return "—"
        try:
            return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return iso

    def _actualizar_estado(self, mensaje=None):
        if mensaje:
            self.estado.config(text=mensaje)
        elif not self._conjuntos:
            self.estado.config(
                text="No hay reglas guardadas todavía. Escribe un nombre y "
                     "pulsa «Guardar actual»."
            )
        else:
            self.estado.config(
                text=f"{len(self._conjuntos)} conjunto(s) guardado(s) en "
                     f"{sesion.DIRECTORIO_REGLAS}"
            )

    def _seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showinfo(
                "Administrar reglas",
                "Selecciona un conjunto de la lista.",
                parent=self,
            )
            return None
        ruta = Path(seleccion[0])
        for conjunto in self._conjuntos:
            if conjunto["ruta"] == ruta:
                return conjunto
        return None

    def _seleccionar_por_nombre(self, nombre):
        for conjunto in self._conjuntos:
            if conjunto["nombre"] == nombre:
                iid = str(conjunto["ruta"])
                if self.tree.exists(iid):
                    self.tree.selection_set(iid)
                    self.tree.focus(iid)
                    self.tree.see(iid)
                return

    # ---------- acciones ----------
    @staticmethod
    def _nombre_valido(nombre):
        return not any(caracter in nombre for caracter in '\\/:*?"<>|')

    def _pedir_nombre(self, titulo, pregunta, inicial=""):
        nombre = simpledialog.askstring(
            titulo, pregunta, initialvalue=inicial, parent=self
        )
        if nombre is None:
            return None
        nombre = nombre.strip()
        if not nombre:
            return None
        if not self._nombre_valido(nombre):
            messagebox.showerror(
                titulo,
                'El nombre no puede contener estos caracteres: \\ / : * ? " < > |',
                parent=self,
            )
            return None
        return nombre

    def _guardar_actual(self):
        texto = self.app.texto_reglas()
        if not texto.strip():
            messagebox.showwarning(
                "Guardar reglas", "No hay reglas para guardar.", parent=self
            )
            return

        nombre = self.nombre_var.get().strip()
        if not nombre:
            nombre = self._pedir_nombre(
                "Guardar reglas",
                "Nombre para este conjunto de reglas:",
            )
            if not nombre:
                return
        elif not self._nombre_valido(nombre):
            messagebox.showerror(
                "Guardar reglas",
                'El nombre no puede contener estos caracteres: \\ / : * ? " < > |',
                parent=self,
            )
            return

        existente = sesion.buscar_conjunto_por_nombre(nombre)
        actual = getattr(self.app, "nombre_reglas_actual", "")
        if existente and existente["nombre"].casefold() != actual.casefold():
            if not messagebox.askyesno(
                "Reemplazar",
                f"Ya existe un conjunto llamado «{existente['nombre']}».\n"
                "¿Reemplazarlo?",
                parent=self,
            ):
                return

        ruta = existente["ruta"] if existente else None
        try:
            sesion.guardar_conjunto(
                nombre, texto, num_reglas=self.app.num_reglas_actual(), ruta=ruta
            )
        except OSError as e:
            messagebox.showerror(
                "Guardar reglas", f"No se pudo guardar: {e}", parent=self
            )
            return

        self.app.nombre_reglas_actual = nombre
        self.app.guardar_sesion()
        self.nombre_var.set(nombre)
        self._cargar_lista()
        self._actualizar_estado(f"Guardado: {nombre}")

    def _cargar_seleccionada(self):
        conjunto = self._seleccionado()
        if conjunto is None:
            return
        # Soltar el grab antes de generar: si las reglas son inválidas,
        # el aviso de la app debe poder recibir clics.
        try:
            self.grab_release()
        except tk.TclError:
            pass
        try:
            self.app.cargar_reglas_guardadas(conjunto["nombre"], conjunto["reglas"])
        finally:
            self.destroy()

    def _renombrar(self):
        conjunto = self._seleccionado()
        if conjunto is None:
            return
        nuevo = self._pedir_nombre(
            "Renombrar", "Nuevo nombre:", inicial=conjunto["nombre"]
        )
        if not nuevo or nuevo.casefold() == conjunto["nombre"].casefold():
            return
        otro = sesion.buscar_conjunto_por_nombre(nuevo)
        if otro:
            messagebox.showerror(
                "Renombrar",
                f"Ya existe un conjunto llamado «{otro['nombre']}».",
                parent=self,
            )
            return
        try:
            sesion.renombrar_conjunto(conjunto["ruta"], nuevo)
        except OSError as e:
            messagebox.showerror(
                "Renombrar", f"No se pudo renombrar: {e}", parent=self
            )
            return

        if getattr(self.app, "nombre_reglas_actual", "").casefold() == \
                conjunto["nombre"].casefold():
            self.app.nombre_reglas_actual = nuevo
            self.app.guardar_sesion()
        self.nombre_var.set(nuevo)
        self._cargar_lista()
        self._actualizar_estado(f"Renombrado: {nuevo}")

    def _duplicar(self):
        conjunto = self._seleccionado()
        if conjunto is None:
            return
        nuevo = self._pedir_nombre(
            "Duplicar", "Nombre de la copia:",
            inicial=f"Copia de {conjunto['nombre']}",
        )
        if not nuevo:
            return
        if sesion.buscar_conjunto_por_nombre(nuevo):
            messagebox.showerror(
                "Duplicar", f"Ya existe un conjunto llamado «{nuevo}».",
                parent=self,
            )
            return
        try:
            sesion.duplicar_conjunto(conjunto["ruta"], nuevo)
        except OSError as e:
            messagebox.showerror(
                "Duplicar", f"No se pudo duplicar: {e}", parent=self
            )
            return
        self._cargar_lista()
        self._seleccionar_por_nombre(nuevo)
        self._actualizar_estado(f"Duplicado: {nuevo}")

    def _eliminar(self):
        conjunto = self._seleccionado()
        if conjunto is None:
            return
        if not messagebox.askyesno(
            "Eliminar",
            f"¿Eliminar «{conjunto['nombre']}»?\n"
            "Esta acción no se puede deshacer.",
            parent=self,
        ):
            return
        try:
            sesion.eliminar_conjunto(conjunto["ruta"])
        except OSError as e:
            messagebox.showerror(
                "Eliminar", f"No se pudo eliminar: {e}", parent=self
            )
            return

        if getattr(self.app, "nombre_reglas_actual", "").casefold() == \
                conjunto["nombre"].casefold():
            self.app.nombre_reglas_actual = ""
            self.app.guardar_sesion()
            self.nombre_var.set("")
        self._cargar_lista()
        self._actualizar_estado(f"Eliminado: {conjunto['nombre']}")
