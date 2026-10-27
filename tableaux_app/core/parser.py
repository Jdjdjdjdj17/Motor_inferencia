# -*- coding: utf-8 -*-
from typing import List
from tableaux_app.core.lexico import Token, tokenizar_conectores
from tableaux_app.core.reescribir import reescribir_si_entonces
from tableaux_app.core.atomos import DiccionarioAtomos
from tableaux_app.core.formulas import Formula, Atom, Not, And, Or, Imp, Iff
from tableaux_app.core.errores import ErrorSintaxis


class Parser:
    def __init__(self, tokens: List[Token], dicc: DiccionarioAtomos):
        self.tokens = tokens
        self.dicc = dicc
        self.pos = 0

    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token('EOF', 'EOF', '')

    def eat(self) -> Token:
        t = self.current()
        self.pos += 1
        return t

    # ---------- mensajes de error ----------
    def _frase_previa(self, k: int = 6) -> str:
        ini = max(0, self.pos - k)
        return ' '.join((t.texto_original or t.valor)
                        for t in self.tokens[ini:self.pos] if t.tipo != 'EOF').strip()

    def _error_inesperado(self) -> ErrorSintaxis:
        t = self.current()
        previo = self._frase_previa()
        generado = (t.tipo == 'IMP' and t.texto_original == '→')  # el → que puso reescribir.py
        if t.tipo in ('EOF', 'COMMA') or generado:
            donde = f" después de «{previo}»" if previo else ""
            return ErrorSintaxis(f"La regla está incompleta{donde}: falta una proposición.")
        palabra = t.texto_original or t.valor
        cerca = f" (cerca de «{(previo + ' ' + palabra).strip()}»)"
        return ErrorSintaxis(f"No esperaba «{palabra}» en este lugar{cerca}.")

    # ---------- gramática ----------
    def parse(self) -> List[Formula]:
        formulas: List[Formula] = []
        while True:
            while self.current().tipo == 'COMMA':
                self.eat()
            if self.current().tipo == 'EOF':
                break
            formulas.append(self.parse_iff())
            if self.current().tipo not in ('COMMA', 'EOF'):
                raise self._error_inesperado()
        return formulas

    def parse_iff(self) -> Formula:
        f = self.parse_imp()
        while self.current().tipo == 'IFF':
            self.eat()
            right = self.parse_imp()
            f = Iff(f, right)
        return f

    def parse_imp(self) -> Formula:
        f = self.parse_or()
        if self.current().tipo == 'IMP':
            self.eat()
            right = self.parse_imp()  # asociativo a derecha
            f = Imp(f, right)
        return f

    def parse_or(self) -> Formula:
        f = self.parse_and()
        while self.current().tipo == 'OR':
            self.eat()
            right = self.parse_and()
            f = Or(f, right)
        return f

    def parse_and(self) -> Formula:
        f = self.parse_not()
        while self.current().tipo == 'AND':
            self.eat()
            right = self.parse_not()
            f = And(f, right)
        return f

    def parse_not(self) -> Formula:
        t = self.current()
        if t.tipo == 'NOT':
            self.eat()
            return Not(self.parse_not())
        if t.tipo == 'LPAREN':
            self.eat()
            f = self.parse_iff()
            if self.current().tipo != 'RPAREN':
                raise ErrorSintaxis("Falta cerrar un paréntesis «)».")
            self.eat()
            return f
        if t.tipo == 'ATOM_TEXT':
            textos = []
            while self.current().tipo == 'ATOM_TEXT':
                tk = self.current()
                textos.append(tk.texto_original or tk.valor)
                self.eat()
            texto = ' '.join(textos)
            letra = self.dicc.obtener_o_crear(texto)
            if not letra:
                raise ErrorSintaxis(f"No pude formar una proposición con «{texto}».")
            return Atom(letra, texto)
        raise self._error_inesperado()


def texto_a_formulas(texto: str, dicc: DiccionarioAtomos = None):
    """Cada línea (Enter) es una regla independiente: ninguna regla se mezcla con la anterior.
    Dentro de una línea, el punto sigue separando oraciones. Los átomos se comparten entre líneas."""
    if dicc is None:
        dicc = DiccionarioAtomos()
    formulas: List[Formula] = []
    for num, linea in enumerate(texto.splitlines(), start=1):
        if not linea.strip():
            continue
        try:
            tokens = tokenizar_conectores(linea)
            tokens2 = reescribir_si_entonces(tokens)
            formulas.extend(Parser(tokens2, dicc).parse())
        except ErrorSintaxis as e:
            raise ErrorSintaxis(f"Línea {num}: {e}") from None
    return formulas, dicc
