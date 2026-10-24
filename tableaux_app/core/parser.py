# -*- coding: utf-8 -*-
from typing import List
from tableaux_app.core.lexico import Token, tokenizar_conectores
from tableaux_app.core.reescribir import reescribir_si_entonces
from tableaux_app.core.atomos import DiccionarioAtomos
from tableaux_app.core.formulas import Formula, Atom, Not, And, Or, Imp, Iff

class Parser:
    def __init__(self, tokens: List[Token], dicc: DiccionarioAtomos):
        self.tokens = tokens
        self.dicc = dicc
        self.pos = 0
    
    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token('EOF','EOF','')
    
    def eat(self, tipo=None):
        t = self.current()
        self.pos += 1
        if self.pos > len(self.tokens) + 5:
            self.pos = len(self.tokens)
        return t
    
    def parse(self) -> List[Formula]:
        formulas = []
        max_iter = 200
        iters = 0
        while iters < max_iter:
            iters += 1
            t = self.current()
            if t.tipo == 'EOF':
                break
            if t.tipo == 'COMMA':
                self.eat()
                continue
            f = self.parse_iff()
            if f:
                formulas.append(f)
            # skip commas
            while self.current().tipo == 'COMMA':
                self.eat()
                if self.current().tipo == 'EOF':
                    break
            if self.current().tipo == 'EOF':
                break
        return formulas
    
    def parse_iff(self):
        f = self.parse_imp()
        while self.current().tipo == 'IFF':
            self.eat()
            right = self.parse_imp()
            f = Iff(f, right)
        return f
    
    def parse_imp(self):
        f = self.parse_or()
        if self.current().tipo == 'IMP':
            self.eat()
            right = self.parse_imp()  # asociativo a derecha
            f = Imp(f, right)
        return f
    
    def parse_or(self):
        f = self.parse_and()
        while self.current().tipo == 'OR':
            self.eat()
            right = self.parse_and()
            f = Or(f, right)
        return f
    
    def parse_and(self):
        f = self.parse_not()
        while self.current().tipo == 'AND':
            self.eat()
            right = self.parse_not()
            f = And(f, right)
        return f
    
    def parse_not(self):
        if self.current().tipo == 'NOT':
            self.eat()
            f = self.parse_not()
            return Not(f)
        if self.current().tipo == 'LPAREN':
            self.eat()
            f = self.parse_iff()
            if self.current().tipo == 'RPAREN':
                self.eat()
            return f
        if self.current().tipo == 'ATOM_TEXT':
            # Agrupar palabras consecutivas en un solo átomo
            palabras = []
            textos_orig = []
            while self.current().tipo == 'ATOM_TEXT':
                t = self.current()
                palabras.append(t.valor)
                textos_orig.append(t.texto_original or t.valor)
                self.eat()
            texto = ' '.join(textos_orig)
            # obtener o crear átomo
            letra = self.dicc.obtener_o_crear(texto)
            if letra:
                return Atom(letra, texto)
            else:
                return Atom('p', texto)
        return None

def texto_a_formulas(texto: str, dicc: DiccionarioAtomos = None):
    if dicc is None:
        dicc = DiccionarioAtomos()
    tokens = tokenizar_conectores(texto)
    tokens2 = reescribir_si_entonces(tokens)
    parser = Parser(tokens2, dicc)
    formulas = parser.parse()
    return formulas, dicc
