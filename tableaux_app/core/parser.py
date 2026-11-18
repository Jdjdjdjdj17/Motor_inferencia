# -*- coding: utf-8 -*-
import re
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


def dividir_oraciones(texto: str) -> List[str]:
    """Parte un texto cualquiera en frases.
    - Separan: . ; : ! ?  (seguidos de espacio) y las líneas en blanco.
    - Un salto de línea separa solo si la línea siguiente empieza con mayúscula y la anterior
      no termina en coma o dos puntos; si no, se considera el mismo texto cortado por el ancho."""
    bloques: List[str] = []
    actual = ''
    for linea in texto.replace('\r', '').split('\n'):
        l = linea.strip()
        if not l:
            if actual:
                bloques.append(actual)
                actual = ''
            continue
        if not actual:
            actual = l
        elif (l[0].isupper() or l[0] in '¿¡') and actual[-1] not in ',:':
            bloques.append(actual)
            actual = l
        else:
            actual += ' ' + l
    if actual:
        bloques.append(actual)
    frases: List[str] = []
    for b in bloques:
        for f in re.split(r'(?<=[.;:!?])\s+', b):
            f = f.strip()
            if f:
                frases.append(f)
    return frases


def localizar_frases(texto: str):
    """Dónde está cada frase de `dividir_oraciones` dentro del texto original.
    Devuelve [(número, frase, inicio, fin)] con la misma numeración que usa texto_a_formulas."""
    resultado = []
    cursor = 0
    for n, frase in enumerate(dividir_oraciones(texto), start=1):
        patron = r'\s+'.join(re.escape(p) for p in frase.split())
        m = re.compile(patron).search(texto, cursor)
        if m is None:
            resultado.append((n, frase, None, None))
            continue
        resultado.append((n, frase, m.start(), m.end()))
        cursor = m.end()
    return resultado


def quitar_frases(texto: str, numeros) -> str:
    """Borra del texto las frases con esos números (los de texto_a_formulas), dejando el resto intacto
    y sin dejar líneas vacías ni espacios sobrantes donde estaban."""
    numeros = set(numeros)
    tramos = [(ini, fin) for n, _, ini, fin in localizar_frases(texto)
              if n in numeros and ini is not None]
    for ini, fin in sorted(tramos, reverse=True):  # de atrás hacia adelante: las posiciones no se mueven
        antes = texto[:ini].rstrip(' \t')
        despues = texto[fin:].lstrip(' \t')
        solo_en_su_linea = (not antes or antes.endswith('\n')) and (not despues or despues.startswith('\n'))
        if solo_en_su_linea:
            if despues.startswith('\n'):
                despues = despues[1:]
            texto = antes + despues
        else:
            pegados = (not antes or antes.endswith('\n') or not despues or despues.startswith('\n'))
            texto = antes + ('' if pegados else ' ') + despues
    return texto


def _es_pregunta(frase: str) -> bool:
    return frase.lstrip().startswith('¿') or frase.rstrip().endswith('?')


def _resumen(frase: str, n: int = 70) -> str:
    return frase if len(frase) <= n else frase[:n - 1] + '…'


def _parsear_frase(frase: str, dicc: DiccionarioAtomos) -> List[Formula]:
    tokens = tokenizar_conectores(frase)
    tokens2 = reescribir_si_entonces(tokens)
    return Parser(tokens2, dicc).parse()


def texto_a_formulas(texto: str, dicc: DiccionarioAtomos = None, omitidas: list = None,
                     fuentes: list = None):
    """Convierte un texto (corto o largo, estructurado o no) en fórmulas.

    omitidas=None -> modo estricto: la primera frase que no se entienda lanza ErrorSintaxis.
    omitidas=[]   -> modo tolerante: las frases que no se entienden (y las preguntas) se anotan en
                     la lista como (número, frase, motivo) y se sigue con el resto.
    fuentes=[]    -> se llena con (número de frase, frase) por cada fórmula devuelta (misma posición),
                     para saber de qué parte del texto salió cada regla.
    """
    if dicc is None:
        dicc = DiccionarioAtomos()
    formulas: List[Formula] = []
    for n, frase in enumerate(dividir_oraciones(texto), start=1):
        if _es_pregunta(frase):
            if omitidas is not None:
                omitidas.append((n, frase, "es una pregunta, no una regla"))
            continue
        if not any(c.isalnum() for c in frase):
            continue
        punto = dicc.punto_de_control()
        try:
            nuevas = _parsear_frase(frase, dicc)
        except ErrorSintaxis as e:
            dicc.restaurar(punto)
            if omitidas is None:
                raise ErrorSintaxis(f"Frase {n} («{_resumen(frase)}»): {e}") from None
            omitidas.append((n, frase, str(e)))
            continue
        formulas.extend(nuevas)
        if fuentes is not None:
            fuentes.extend([(n, frase)] * len(nuevas))
    return formulas, dicc
