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

def _render(f: Formula):
    """Devuelve (texto, precedencia) para poder poner paréntesis solo cuando hace falta.

    Precedencia: ¬ (4) > ∧ (3) > ∨ (2) > → (1) > ↔ (0).
    """
    if isinstance(f, Atom):
        return f.id, 5

    if isinstance(f, Not):
        inner, prec = _render(f.f)
        if prec < 4:
            inner = f'({inner})'
        return f'¬{inner}', 4

    if isinstance(f, And):
        return _binaria(f, '∧', 3, 'izquierda')

    if isinstance(f, Or):
        return _binaria(f, '∨', 2, 'izquierda')

    if isinstance(f, Imp):
        return _binaria(f, '→', 1, 'derecha')

    if isinstance(f, Iff):
        return _binaria(f, '↔', 0, 'ninguna')

    return str(f), 5


def _binaria(f, simbolo: str, prec: int, asociatividad: str):
    """Arma «izq símbolo der» con paréntesis según precedencia y asociatividad."""
    izq, p_izq = _render(f.left)
    der, p_der = _render(f.right)

    if p_izq < prec or (p_izq == prec and asociatividad != 'izquierda'):
        izq = f'({izq})'
    if p_der < prec or (p_der == prec and asociatividad != 'derecha'):
        der = f'({der})'

    return f'{izq} {simbolo} {der}', prec


def formula_a_string(f: Formula) -> str:
    return _render(f)[0]
