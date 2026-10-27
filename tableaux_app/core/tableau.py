# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional
from tableaux_app.core.formulas import Formula, Atom, Not, And, Or, Imp, Iff, es_literal, formula_a_string

@dataclass
class TableauNode:
    id: int
    formulas: List[Formula] = field(default_factory=list)
    applied: Set[int] = field(default_factory=set)
    status: str = "open"  # open, closed, internal
    rule: str = ""  # "α" o "β": qué tipo de expansión creó este nodo
    generada_por: Optional[Formula] = None  # fórmula del padre que se expandió
    lado: str = ""  # en una β: "izquierda" o "derecha"
    closes_with: Optional[Tuple[Formula, Formula]] = None
    children: List['TableauNode'] = field(default_factory=list)
    parent_id: Optional[int] = None

class Tableau:
    def __init__(self, formulas_iniciales: List[Formula]):
        self.next_id = 0
        self.root = self.crear_nodo(formulas_iniciales[:], parent_id=None, applied=set())
        self.nodes = {}
        self.registrar(self.root)
    
    def crear_nodo(self, formulas, parent_id=None, applied=None, rule="", generada_por=None, lado=""):
        if applied is None:
            applied_set = set()
        else:
            applied_set = set(applied)
        n = TableauNode(id=self.next_id, formulas=formulas[:], applied=applied_set,
                        parent_id=parent_id, rule=rule, generada_por=generada_por, lado=lado)
        self.next_id += 1
        return n
    
    def registrar(self, node):
        self.nodes[node.id] = node
    
    def es_literal(self, f: Formula) -> bool:
        return es_literal(f)
    
    def obtener_complemento_literal(self, f: Formula) -> Optional[Formula]:
        if isinstance(f, Atom):
            return Not(f)
        if isinstance(f, Not) and isinstance(f.f, Atom):
            return f.f
        return None
    
    def chequear_cierre(self, node: TableauNode) -> bool:
        # Buscar par (L, ¬L)
        literales = []
        for f in node.formulas:
            if self.es_literal(f):
                literales.append(f)
        # comparar
        for i, l1 in enumerate(literales):
            c1 = self.obtener_complemento_literal(l1)
            if c1 is None:
                continue
            for l2 in literales[i+1:]:
                # comparar igualdad
                if self.son_formulas_iguales(c1, l2):
                    node.status = "closed"
                    node.closes_with = (l1, l2)
                    return True
                if self.son_formulas_iguales(l1, self.obtener_complemento_literal(l2)):
                    node.status = "closed"
                    node.closes_with = (l1, l2)
                    return True
        return False
    
    def son_formulas_iguales(self, a: Formula, b: Formula) -> bool:
        if type(a) != type(b):
            return False
        if isinstance(a, Atom) and isinstance(b, Atom):
            return a.id == b.id
        if isinstance(a, Not) and isinstance(b, Not):
            return self.son_formulas_iguales(a.f, b.f)
        if isinstance(a, And) and isinstance(b, And):
            return (self.son_formulas_iguales(a.left,b.left) and self.son_formulas_iguales(a.right,b.right)) or \
                   (self.son_formulas_iguales(a.left,b.right) and self.son_formulas_iguales(a.right,b.left))
        if isinstance(a, Or) and isinstance(b, Or):
            return (self.son_formulas_iguales(a.left,b.left) and self.son_formulas_iguales(a.right,b.right)) or \
                   (self.son_formulas_iguales(a.left,b.right) and self.son_formulas_iguales(a.right,b.left))
        if isinstance(a, Imp) and isinstance(b, Imp):
            return self.son_formulas_iguales(a.left,b.left) and self.son_formulas_iguales(a.right,b.right)
        if isinstance(a, Iff) and isinstance(b, Iff):
            return (self.son_formulas_iguales(a.left,b.left) and self.son_formulas_iguales(a.right,b.right)) or \
                   (self.son_formulas_iguales(a.left,b.right) and self.son_formulas_iguales(a.right,b.left))
        return False
    
    def es_alpha(self, f: Formula) -> bool:
        if isinstance(f, And):
            return True
        if isinstance(f, Not):
            nf = f.f
            if isinstance(nf, Or):
                return True  # ¬(A ∨ B)
            if isinstance(nf, Imp):
                return True  # ¬(A → B)
            if isinstance(nf, And):
                return False  # ¬(A ∧ B) es beta
            if isinstance(nf, Iff):
                return False  # ¬(A ↔ B) es beta
            if isinstance(nf, Not):
                return True  # ¬¬A
        return False
    
    def expandir_alpha(self, f: Formula) -> List[Formula]:
        if isinstance(f, And):
            return [f.left, f.right]
        if isinstance(f, Not):
            nf = f.f
            if isinstance(nf, Not):
                return [nf.f]  # ¬¬A
            if isinstance(nf, Or):
                # ¬(A ∨ B) -> ¬A, ¬B
                return [Not(nf.left), Not(nf.right)]
            if isinstance(nf, Imp):
                # ¬(A → B) -> A, ¬B
                return [nf.left, Not(nf.right)]
        return []
    
    def expandir_beta(self, f: Formula) -> Tuple[List[Formula], List[Formula]]:
        if isinstance(f, Or):
            return ([f.left], [f.right])
        if isinstance(f, Imp):
            # A → B -> ¬A | B
            return ([Not(f.left)], [f.right])
        if isinstance(f, Iff):
            # (A,B) | (¬A,¬B)
            return ([f.left, f.right], [Not(f.left), Not(f.right)])
        if isinstance(f, Not):
            nf = f.f
            if isinstance(nf, And):
                # ¬(A ∧ B) -> ¬A | ¬B
                return ([Not(nf.left)], [Not(nf.right)])
            if isinstance(nf, Iff):
                # ¬(A ↔ B) -> (A,¬B) | (¬A,B)
                return ([nf.left, Not(nf.right)], [Not(nf.left), nf.right])
        return ([], [])
    
    def encontrar_pendiente(self, node: TableauNode) -> Optional[int]:
        # α antes que β - buscar primero fórmula alpha no aplicada
        for idx, f in enumerate(node.formulas):
            if idx in node.applied:
                continue
            if self.es_literal(f):
                continue
            if self.es_alpha(f):
                return idx
        # luego beta
        for idx, f in enumerate(node.formulas):
            if idx in node.applied:
                continue
            if self.es_literal(f):
                continue
            return idx
        return None
    
    def expandir_nodo(self, node: TableauNode):
        if node.status == "closed":
            return
        if self.chequear_cierre(node):
            return
        pendiente = self.encontrar_pendiente(node)
        if pendiente is None:
            # solo literales
            if self.chequear_cierre(node):
                return
            node.status = "open"
            return
        f = node.formulas[pendiente]
        node.applied.add(pendiente)
        if self.es_alpha(f):
            nuevos = self.expandir_alpha(f)
            nuevo_nodo = self.crear_nodo(node.formulas + nuevos, parent_id=node.id,
                                         applied=node.applied, rule="α", generada_por=f)
            node.children = [nuevo_nodo]
            self.registrar(nuevo_nodo)
            self.chequear_cierre(nuevo_nodo)
            self.expandir_nodo(nuevo_nodo)
        else:
            izq_list, der_list = self.expandir_beta(f)
            hijo_izq = self.crear_nodo(node.formulas + izq_list, parent_id=node.id,
                                       applied=node.applied, rule="β", generada_por=f, lado="izquierda")
            hijo_der = self.crear_nodo(node.formulas + der_list, parent_id=node.id,
                                       applied=node.applied, rule="β", generada_por=f, lado="derecha")
            node.children = [hijo_izq, hijo_der]
            self.registrar(hijo_izq)
            self.registrar(hijo_der)
            for h in node.children:
                self.chequear_cierre(h)
                self.expandir_nodo(h)
    
    def expandir(self):
        self.expandir_nodo(self.root)
    
    def obtener_ramas(self):
        """Todas las ramas del árbol (abiertas y cerradas), en orden.
        Cada rama es el camino completo desde la raíz hasta una hoja."""
        ramas = []

        def dfs(n, camino):
            camino = camino + [n]
            if not n.children:
                ramas.append({
                    'numero': len(ramas) + 1,
                    'nodos': camino,
                    'hoja': n,
                    'formulas': list(n.formulas),
                    'estado': 'cerrada' if n.status == 'closed' else 'abierta',
                    'cierre': n.closes_with,
                })
                return
            for c in n.children:
                dfs(c, camino)

        dfs(self.root, [])
        return ramas

    def asignacion_de_rama(self, rama, dicc):
        """Valores de los átomos en una rama: V si aparece, F si aparece negado,
        «—» si no aparece (libre)."""
        asignacion = {}
        for letra in dicc.atomos:
            valor = '—'
            for f in rama['formulas']:
                if isinstance(f, Atom) and f.id == letra:
                    valor = 'V'
                    break
                if isinstance(f, Not) and isinstance(f.f, Atom) and f.f.id == letra:
                    valor = 'F'
                    break
            asignacion[letra] = valor
        return asignacion

    def obtener_hojas_abiertas(self):
        hojas = []
        def dfs(n):
            if n.status == "closed":
                return
            if len(n.children) == 0:
                if n.status == "open" or (n.status != "closed" and not self.chequear_cierre(n)):
                    # verificar
                    if not self.chequear_cierre(n):
                        hojas.append(n)
                return
            for c in n.children:
                dfs(c)
        dfs(self.root)
        # filtrar cerradas
        res = []
        for h in hojas:
            if h.status == "closed":
                continue
            # re-chequear
            if self.chequear_cierre(h):
                continue
            res.append(h)
        return res
    
    def extraer_modelos(self, dicc):
        modelos = []
        hojas = self.obtener_hojas_abiertas()
        for h in hojas:
            asignacion = {}
            # revisar todos los átomos
            for letra, info in dicc.atomos.items():
                # buscar literal
                pos_atom = None  # None = libre
                for f in h.formulas:
                    if isinstance(f, Atom) and f.id == letra:
                        pos_atom = True
                        break
                    if isinstance(f, Not) and isinstance(f.f, Atom) and f.f.id == letra:
                        pos_atom = False
                        break
                if pos_atom is True:
                    asignacion[letra] = 'V'
                elif pos_atom is False:
                    asignacion[letra] = 'F'
                else:
                    asignacion[letra] = '—'  # libre
            modelos.append(asignacion)
        return modelos
