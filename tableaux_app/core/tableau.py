# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional
from tableaux_app.core.formulas import Formula, Atom, Not, And, Or, Imp, Iff, es_literal
from tableaux_app.core.errores import ArbolDemasiadoGrande

# Si el árbol "clásico" pasa de este tamaño, se vuelve a intentar en modo compacto.
LIMITE_CLASICO = 600
# Tope absoluto de nodos (protege la memoria con textos enormes).
LIMITE_COMPACTO = 20000


@dataclass
class TableauNode:
    id: int
    formulas: List[Formula] = field(default_factory=list)
    applied: Set[int] = field(default_factory=set)
    status: str = "open"  # open, closed, internal
    rule: str = ""  # alpha, beta
    closes_with: Optional[Tuple[Formula, Formula]] = None
    generada_por: Optional[Formula] = None  # fórmula cuya expansión creó este nodo (None en la raíz)
    lado: str = ""  # 'izquierda' / 'derecha' cuando el nodo viene de una bifurcación β
    origenes: List[Formula] = field(default_factory=list)  # modo compacto: fórmulas resueltas en este paso
    children: List['TableauNode'] = field(default_factory=list)
    parent_id: Optional[int] = None


class Tableau:
    """
    Tableau semántico (reglas α/β).

    modo='clasico'  : una fórmula por paso; cada β bifurca siempre (el método de libro).
    modo='compacto' : en cada nodo aplica todas las α juntas y resuelve sin bifurcar las β que
                      ya están decididas (una rama se cierra sola o ya se cumple). Da los mismos
                      resultados con muchísimas menos ramas: sirve para textos grandes.
    modo='auto'     : empieza clásico y, si el árbol se pasa de LIMITE_CLASICO nodos, cambia a compacto.
    """

    def __init__(self, formulas_iniciales: List[Formula], modo: str = 'auto',
                 limite_clasico: int = LIMITE_CLASICO, limite_compacto: int = LIMITE_COMPACTO):
        self.formulas_iniciales = list(formulas_iniciales)
        self.modo_pedido = modo
        self.modo = None  # 'clásico' o 'compacto' (se fija al expandir)
        self.limite_clasico = limite_clasico
        self.limite_compacto = limite_compacto
        self._reiniciar()

    def _reiniciar(self):
        self.next_id = 0
        self.nodes = {}
        self.root = self.crear_nodo(self.formulas_iniciales[:], parent_id=None, applied=set())
        self.registrar(self.root)

    def crear_nodo(self, formulas, parent_id=None, applied=None):
        applied_set = set(applied) if applied is not None else set()
        n = TableauNode(id=self.next_id, formulas=formulas[:], applied=applied_set, parent_id=parent_id)
        self.next_id += 1
        return n

    def registrar(self, node):
        self.nodes[node.id] = node

    def _hijo(self, padre: TableauNode, nuevas: List[Formula]) -> TableauNode:
        h = self.crear_nodo(padre.formulas + nuevas, parent_id=padre.id, applied=padre.applied)
        self.registrar(h)
        return h

    def es_literal(self, f: Formula) -> bool:
        return es_literal(f)

    def obtener_complemento_literal(self, f: Formula) -> Optional[Formula]:
        if isinstance(f, Atom):
            return Not(f)
        if isinstance(f, Not) and isinstance(f.f, Atom):
            return f.f
        return None

    def chequear_cierre(self, node: TableauNode) -> bool:
        """Cierra el nodo si contiene un átomo y su negación (revisión lineal)."""
        if node.status == "closed":
            return True
        pos, neg = {}, {}
        for f in node.formulas:
            if isinstance(f, Atom):
                if f.id in neg:
                    node.status = "closed"
                    node.closes_with = (neg[f.id], f)
                    return True
                pos.setdefault(f.id, f)
            elif isinstance(f, Not) and isinstance(f.f, Atom):
                if f.f.id in pos:
                    node.status = "closed"
                    node.closes_with = (pos[f.f.id], f)
                    return True
                neg.setdefault(f.f.id, f)
        return False

    def son_formulas_iguales(self, a: Formula, b: Formula) -> bool:
        if type(a) != type(b):
            return False
        if isinstance(a, Atom) and isinstance(b, Atom):
            return a.id == b.id
        if isinstance(a, Not) and isinstance(b, Not):
            return self.son_formulas_iguales(a.f, b.f)
        if isinstance(a, And) and isinstance(b, And):
            return (self.son_formulas_iguales(a.left, b.left) and self.son_formulas_iguales(a.right, b.right)) or \
                   (self.son_formulas_iguales(a.left, b.right) and self.son_formulas_iguales(a.right, b.left))
        if isinstance(a, Or) and isinstance(b, Or):
            return (self.son_formulas_iguales(a.left, b.left) and self.son_formulas_iguales(a.right, b.right)) or \
                   (self.son_formulas_iguales(a.left, b.right) and self.son_formulas_iguales(a.right, b.left))
        if isinstance(a, Imp) and isinstance(b, Imp):
            return self.son_formulas_iguales(a.left, b.left) and self.son_formulas_iguales(a.right, b.right)
        if isinstance(a, Iff) and isinstance(b, Iff):
            return (self.son_formulas_iguales(a.left, b.left) and self.son_formulas_iguales(a.right, b.right)) or \
                   (self.son_formulas_iguales(a.left, b.right) and self.son_formulas_iguales(a.right, b.left))
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
                return [Not(nf.left), Not(nf.right)]  # ¬(A ∨ B) -> ¬A, ¬B
            if isinstance(nf, Imp):
                return [nf.left, Not(nf.right)]  # ¬(A → B) -> A, ¬B
        return []

    def expandir_beta(self, f: Formula) -> Tuple[List[Formula], List[Formula]]:
        if isinstance(f, Or):
            return ([f.left], [f.right])
        if isinstance(f, Imp):
            return ([Not(f.left)], [f.right])  # A → B -> ¬A | B
        if isinstance(f, Iff):
            return ([f.left, f.right], [Not(f.left), Not(f.right)])  # (A,B) | (¬A,¬B)
        if isinstance(f, Not):
            nf = f.f
            if isinstance(nf, And):
                return ([Not(nf.left)], [Not(nf.right)])  # ¬(A ∧ B) -> ¬A | ¬B
            if isinstance(nf, Iff):
                return ([nf.left, Not(nf.right)], [Not(nf.left), nf.right])  # (A,¬B) | (¬A,B)
        return ([], [])

    def encontrar_pendiente(self, node: TableauNode) -> Optional[int]:
        # α antes que β
        for idx, f in enumerate(node.formulas):
            if idx in node.applied or self.es_literal(f):
                continue
            if self.es_alpha(f):
                return idx
        for idx, f in enumerate(node.formulas):
            if idx in node.applied or self.es_literal(f):
                continue
            return idx
        return None

    # ------------------------------------------------------------------ expansión
    def expandir(self):
        if self.modo_pedido == 'clasico':
            self._expandir_clasico(self.limite_compacto)
            self.modo = 'clásico'
        elif self.modo_pedido == 'compacto':
            self._expandir_compacto(self.limite_compacto)
            self.modo = 'compacto'
        else:
            try:
                self._expandir_clasico(self.limite_clasico)
                self.modo = 'clásico'
            except ArbolDemasiadoGrande:
                self._reiniciar()
                self._expandir_compacto(self.limite_compacto)
                self.modo = 'compacto'

    def _revisar_limite(self, limite: int):
        if len(self.nodes) > limite:
            raise ArbolDemasiadoGrande(
                f"El árbol pasó de {limite} nodos. Hay demasiadas reglas con «o» o «si… entonces» "
                f"que no se resuelven entre sí y las ramas crecen sin control. "
                f"Prueba con menos reglas o separa el texto en partes."
            )

    def _expandir_clasico(self, limite: int):
        """Una fórmula por paso. α no bifurca; β siempre bifurca. Iterativo (sin recursión)."""
        pila = [self.root]
        while pila:
            node = pila.pop()
            if self.chequear_cierre(node):
                continue
            idx = self.encontrar_pendiente(node)
            if idx is None:
                node.status = "open"
                continue
            f = node.formulas[idx]
            node.applied.add(idx)
            node.status = "internal"
            if self.es_alpha(f):
                node.rule = "alpha"
                h = self._hijo(node, self.expandir_alpha(f))
                h.generada_por = f
                node.children = [h]
                pila.append(h)
            else:
                node.rule = "beta"
                izq, der = self.expandir_beta(f)
                hi = self._hijo(node, izq)
                hd = self._hijo(node, der)
                hi.generada_por = hd.generada_por = f
                hi.lado, hd.lado = "izquierda", "derecha"
                node.children = [hi, hd]
                pila.append(hd)
                pila.append(hi)
            self._revisar_limite(limite)

    # --- modo compacto
    @staticmethod
    def _registrar_literal(f: Formula, pos: set, neg: set) -> bool:
        """Anota un literal. Devuelve True si crea una contradicción."""
        if isinstance(f, Atom):
            pos.add(f.id)
            return f.id in neg
        if isinstance(f, Not) and isinstance(f.f, Atom):
            neg.add(f.f.id)
            return f.f.id in pos
        return False

    @staticmethod
    def _cumple(lista: List[Formula], pos: set, neg: set) -> bool:
        """Todos los elementos son literales que ya están en la rama."""
        for x in lista:
            if isinstance(x, Atom):
                if x.id not in pos:
                    return False
            elif isinstance(x, Not) and isinstance(x.f, Atom):
                if x.f.id not in neg:
                    return False
            else:
                return False
        return True

    @staticmethod
    def _cierra(lista: List[Formula], pos: set, neg: set) -> bool:
        """Algún literal de la lista contradice la rama."""
        for x in lista:
            if isinstance(x, Atom) and x.id in neg:
                return True
            if isinstance(x, Not) and isinstance(x.f, Atom) and x.f.id in pos:
                return True
        return False

    def _saturar(self, node: TableauNode) -> TableauNode:
        """Aplica todas las α y las β ya decididas. Devuelve el nodo con el que seguir
        (un hijo con las fórmulas nuevas, o el mismo nodo si no había nada que hacer)."""
        trabajo = list(node.formulas)
        applied = set(node.applied)
        pos, neg = set(), set()
        for f in trabajo:
            self._registrar_literal(f, pos, neg)
        conflicto = False
        origenes: List[Formula] = []
        cambiado = True
        while cambiado and not conflicto:
            cambiado = False
            for idx in range(len(trabajo)):
                if conflicto:
                    break
                if idx in applied:
                    continue
                f = trabajo[idx]
                if self.es_literal(f):
                    continue
                if self.es_alpha(f):
                    applied.add(idx)
                    origenes.append(f)
                    for x in self.expandir_alpha(f):
                        trabajo.append(x)
                        if self._registrar_literal(x, pos, neg):
                            conflicto = True
                    cambiado = True
                    continue
                izq, der = self.expandir_beta(f)
                if self._cumple(izq, pos, neg) or self._cumple(der, pos, neg):
                    applied.add(idx)  # ya se cumple: no hace falta bifurcar
                    cambiado = True
                    continue
                cierra_i = self._cierra(izq, pos, neg)
                cierra_d = self._cierra(der, pos, neg)
                if cierra_i and not cierra_d:
                    elegido = der
                elif cierra_d:
                    elegido = izq  # (si cierran ambas, la rama se cerrará sola)
                else:
                    continue  # sigue sin decidirse: se bifurcará después
                applied.add(idx)
                origenes.append(f)
                for x in elegido:
                    trabajo.append(x)
                    if self._registrar_literal(x, pos, neg):
                        conflicto = True
                cambiado = True
        if len(trabajo) == len(node.formulas):
            node.applied = applied  # solo se descartaron β que ya se cumplían: no hay nodo nuevo
            return node
        h = self.crear_nodo(trabajo, parent_id=node.id, applied=applied)
        h.rule = "propagacion"
        h.origenes = origenes
        h.generada_por = origenes[0] if origenes else None
        self.registrar(h)
        node.children = [h]
        node.status = "internal"
        node.rule = "alpha"
        return h

    def _expandir_compacto(self, limite: int):
        pila = [self.root]
        while pila:
            node = pila.pop()
            if self.chequear_cierre(node):
                continue
            node = self._saturar(node)
            if self.chequear_cierre(node):
                continue
            idx = self.encontrar_pendiente(node)
            if idx is None:
                node.status = "open"
                continue
            f = node.formulas[idx]
            node.applied.add(idx)
            node.status = "internal"
            node.rule = "beta"
            izq, der = self.expandir_beta(f)
            hi = self._hijo(node, izq)
            hd = self._hijo(node, der)
            hi.generada_por = hd.generada_por = f
            hi.lado, hd.lado = "izquierda", "derecha"
            node.children = [hi, hd]
            pila.append(hd)
            pila.append(hi)
            self._revisar_limite(limite)

    # ------------------------------------------------------------------ resultados
    def obtener_hojas_abiertas(self):
        hojas = []
        pila = [self.root]
        while pila:
            n = pila.pop()
            if n.status == "closed":
                continue
            if not n.children:
                if not self.chequear_cierre(n):
                    hojas.append(n)
                continue
            pila.extend(reversed(n.children))
        return hojas

    def extraer_modelos(self, dicc, max_modelos: Optional[int] = None):
        modelos = []
        hojas = self.obtener_hojas_abiertas()
        if max_modelos is not None:
            hojas = hojas[:max_modelos]
        for h in hojas:
            pos, neg = set(), set()
            for f in h.formulas:
                if isinstance(f, Atom):
                    pos.add(f.id)
                elif isinstance(f, Not) and isinstance(f.f, Atom):
                    neg.add(f.f.id)
            asignacion = {}
            for letra in dicc.atomos:
                if letra in pos:
                    asignacion[letra] = 'V'
                elif letra in neg:
                    asignacion[letra] = 'F'
                else:
                    asignacion[letra] = '—'  # libre
            modelos.append(asignacion)
        return modelos

    def _asignacion(self, hoja, dicc):
        """V / F / — (libre) para cada átomo, según los literales de una hoja."""
        pos, neg = set(), set()
        for f in hoja.formulas:
            if isinstance(f, Atom):
                pos.add(f.id)
            elif isinstance(f, Not) and isinstance(f.f, Atom):
                neg.add(f.f.id)
        asignacion = {}
        for letra in dicc.atomos:
            asignacion[letra] = 'V' if letra in pos else 'F' if letra in neg else '—'
        return asignacion

    def asignacion_de_rama(self, rama, dicc):
        return self._asignacion(rama['hoja'], dicc)

    def obtener_ramas(self):
        """Todas las ramas (hojas), de izquierda a derecha, con su camino desde la raíz."""
        ramas = []
        pila = [(self.root, [self.root])]
        while pila:
            n, camino = pila.pop()
            if not n.children:
                self.chequear_cierre(n)
                ramas.append({
                    'numero': 0,
                    'hoja': n,
                    'nodos': camino,
                    'formulas': n.formulas,
                    'estado': 'cerrada' if n.status == 'closed' else 'abierta',
                    'cierre': n.closes_with,
                })
                continue
            for h in reversed(n.children):
                pila.append((h, camino + [h]))
        for i, r in enumerate(ramas, start=1):
            r['numero'] = i
        return ramas
