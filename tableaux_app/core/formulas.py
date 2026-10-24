# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import List, Union

@dataclass
class Formula:
    pass

@dataclass
class Atom(Formula):
    id: str  # p, q, r,...
    texto: str  # texto original canónico

@dataclass
class Not(Formula):
    f: Formula

@dataclass
class And(Formula):
    left: Formula
    right: Formula

@dataclass
class Or(Formula):
    left: Formula
    right: Formula

@dataclass
class Imp(Formula):
    left: Formula
    right: Formula  # p -> q

@dataclass
class Iff(Formula):
    left: Formula
    right: Formula  # p <-> q

def es_literal(f: Formula) -> bool:
    if isinstance(f, Atom):
        return True
    if isinstance(f, Not) and isinstance(f.f, Atom):
        return True
    return False

def complemento(f: Formula) -> Formula:
    """Retorna el complemento literal si es literal, sino Not(f)."""
    if isinstance(f, Atom):
        return Not(f)
    if isinstance(f, Not) and isinstance(f.f, Atom):
        return f.f
    return Not(f)

def formula_a_string(f: Formula) -> str:
    if isinstance(f, Atom):
        return f.id
    if isinstance(f, Not):
        if isinstance(f.f, Atom):
            return f'¬{f.f.id}'
        # ¬¬A
        if isinstance(f.f, Not):
            return formula_a_string(f.f.f)
        # Necesita paréntesis para no-(...)
        inner = formula_a_string(f.f)
        # Si es binaria compleja
        if isinstance(f.f, (And, Or, Imp, Iff)):
            return f'¬({inner})'
        return f'¬{inner}'
    if isinstance(f, And):
        left_s = formula_a_string(f.left)
        right_s = formula_a_string(f.right)
        # Añadir paréntesis si hijo tiene menor precedencia? 
        # and > or/imp/iff en algunos casos, pero para mostrar bien
        lpar = ''
        rpar = ''
        if isinstance(f.left, (Or, Imp, Iff)):
            lpar, rpar_left = '(', ')'
            left_s = '(' + formula_a_string(f.left) + ')'
        else:
            left_s = formula_a_string(f.left)
        if isinstance(f.right, (Or, Imp, Iff)):
            right_s = '(' + formula_a_string(f.right) + ')'
        else:
            right_s = formula_a_string(f.right)
        return f'{left_s} ∧ {right_s}'
    if isinstance(f, Or):
        left_s = formula_a_string(f.left)
        right_s = formula_a_string(f.right)
        if isinstance(f.left, (Imp, Iff)):
            left_s = '(' + formula_a_string(f.left) + ')'
        else:
            left_s = formula_a_string(f.left)
        if isinstance(f.right, (Imp, Iff)):
            right_s = '(' + formula_a_string(f.right) + ')'
        else:
            right_s = formula_a_string(f.right)
        return f'{left_s} ∨ {right_s}'
    if isinstance(f, Imp):
        left_s = formula_a_string(f.left)
        right_s = formula_a_string(f.right)
        if isinstance(f.left, Iff):
            left_s = '(' + formula_a_string(f.left) + ')'
        else:
            left_s = formula_a_string(f.left)
        if isinstance(f.right, (Imp, Iff)):  # asociativo a derecha pero para claridad
            right_s = '(' + formula_a_string(f.right) + ')'
        else:
            right_s = formula_a_string(f.right)
        return f'{left_s} → {right_s}'
    if isinstance(f, Iff):
        left_s = '(' + formula_a_string(f.left) + ')'
        right_s = '(' + formula_a_string(f.right) + ')'
        return f'{left_s} ↔ {right_s}'
    return str(f)
