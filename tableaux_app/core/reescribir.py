# -*- coding: utf-8 -*-
"""
Reescritura de condicionales en español a implicaciones (todo termina como P → Q).

Formas que entiende:
  Si P, entonces Q.   Si P entonces Q.   Si P, Q.          (condicional directo)
  Q, si P.   Q cuando P.   Q porque P.   Q siempre que P.  (condicional invertido)
  P, luego Q.   P, por lo tanto Q.                         (conclusión suelta)

Si algo no se puede interpretar se lanza ErrorSintaxis: nunca se descarta en silencio.
"""
from typing import List, Tuple
from tableaux_app.core.lexico import Token
from tableaux_app.core.errores import ErrorSintaxis


def _imp() -> Token:
    return Token('IMP', 'IMP', '→')


def _coma() -> Token:
    return Token('COMMA', ',', ',')


def _texto(tokens: List[Token]) -> str:
    return ' '.join((t.texto_original or t.valor) for t in tokens).strip()


# Tras estos tokens, un "ni" no necesita un "y" delante.
_NO_PRECEDE_AND = {'COMMA', 'LPAREN', 'AND', 'OR', 'IMP', 'IFF', 'NOT', 'IF', 'THEN'}


def _expandir_ni(tokens: List[Token]) -> List[Token]:
    """'no llueve ni nieva' / 'ni A ni B'  →  ¬A ∧ ¬B (inserta el 'y' que falta)."""
    out: List[Token] = []
    for t in tokens:
        if t.tipo == 'NOT' and t.texto_original == 'ni' and out and out[-1].tipo not in _NO_PRECEDE_AND:
            out.append(Token('AND', 'AND', 'ni'))
        out.append(t)
    return out


_FIN_DE_ORACION = ('.', ';', '\n')


def _quitar_conjuncion_inicial(tokens: List[Token]) -> List[Token]:
    """'Y no tengo libro.' / 'Pero llueve.' al inicio de una oración: la 'y' solo enlaza con
    la regla anterior (las reglas ya se leen todas juntas), así que se ignora."""
    out: List[Token] = []
    for t in tokens:
        if t.tipo == 'AND' and (not out or (out[-1].tipo == 'COMMA' and out[-1].texto_original in _FIN_DE_ORACION)):
            continue
        out.append(t)
    return out


def _leer_hasta(tokens: List[Token], i: int, paradas) -> Tuple[List[Token], int]:
    """Lee tokens desde i hasta un token de `paradas` a nivel 0 de paréntesis.
    Se detiene (sin consumir) en EOF o en un ')' que no abrimos nosotros."""
    n = len(tokens)
    out: List[Token] = []
    prof = 0
    while i < n:
        t = tokens[i]
        if t.tipo == 'EOF':
            break
        if t.tipo == 'LPAREN':
            prof += 1
        elif t.tipo == 'RPAREN':
            if prof == 0:
                break
            prof -= 1
        elif prof == 0 and t.tipo in paradas:
            break
        out.append(t)
        i += 1
    return out, i


def _sacar_ultima_oracion(res: List[Token]) -> List[Token]:
    """Quita de `res` y devuelve la última oración ya emitida
    (lo que hay después del último separador, respetando paréntesis)."""
    while res and res[-1].tipo == 'COMMA':
        res.pop()
    j = len(res)
    prof = 0
    while j > 0:
        t = res[j - 1]
        if t.tipo == 'RPAREN':
            prof += 1
        elif t.tipo == 'LPAREN':
            if prof == 0:
                break
            prof -= 1
        elif t.tipo == 'COMMA' and prof == 0:
            break
        j -= 1
    oracion = res[j:]
    del res[j:]
    return oracion


def _emitir(res: List[Token], ant: List[Token], cons: List[Token], tokens: List[Token], i: int) -> None:
    res.extend(ant)
    res.append(_imp())
    res.extend(cons)
    # Dentro de un paréntesis no se pone separador antes del ')'
    if i >= len(tokens) or tokens[i].tipo != 'RPAREN':
        res.append(_coma())


def _condicional_directo(tokens: List[Token], i: int, res: List[Token]) -> int:
    """'Si P, entonces Q' / 'Si P entonces Q' / 'Si P, Q'.
    También cubre 'Q, si P.': si tras la condición no hay consecuente, está en la oración anterior."""
    i += 1  # saltar el IF
    ant, i = _leer_hasta(tokens, i, {'THEN', 'COMMA'})
    if not ant:
        raise ErrorSintaxis("Después de «si» (o «cuando», «porque»…) no hay ninguna condición.")

    hay_consecuente = False
    if i < len(tokens) and tokens[i].tipo == 'THEN':
        i += 1
        hay_consecuente = True
    elif i < len(tokens) and tokens[i].tipo == 'COMMA':
        sep = tokens[i]
        i += 1
        if i < len(tokens) and tokens[i].tipo == 'THEN':
            i += 1
            hay_consecuente = True
        elif sep.texto_original == ',':
            hay_consecuente = True

    if hay_consecuente:
        cons, i = _leer_hasta(tokens, i, {'COMMA', 'IF'})
        if not cons:
            raise ErrorSintaxis(f"A la condición «{_texto(ant)}» le falta lo que ocurre (después de «entonces» o de la coma).")
    else:
        cons = _sacar_ultima_oracion(res)
        if not cons:
            raise ErrorSintaxis(f"A la condición «{_texto(ant)}» le falta el consecuente. Escribe «si {_texto(ant)}, entonces ...».")

    _emitir(res, ant, cons, tokens, i)
    return i


def _condicional_invertido(tokens: List[Token], i: int, res: List[Token]) -> int:
    """'Q si P' / 'Q cuando P' / 'Q porque P'  →  P → Q."""
    cons = _sacar_ultima_oracion(res)
    palabra = tokens[i].texto_original or 'si'
    i += 1
    ant, i = _leer_hasta(tokens, i, {'COMMA'})
    if not ant:
        raise ErrorSintaxis(f"Después de «{palabra}» no hay ninguna condición.")
    if not cons:
        raise ErrorSintaxis(f"Antes de «{palabra} {_texto(ant)}» falta lo que ocurre.")
    if i < len(tokens) and tokens[i].tipo == 'COMMA':
        i += 1
    _emitir(res, ant, cons, tokens, i)
    return i


def _conclusion_suelta(tokens: List[Token], i: int, res: List[Token]) -> int:
    """'P, luego Q' / 'P, por lo tanto Q' (sin un 'si' antes)  →  P → Q."""
    palabra = tokens[i].texto_original or 'entonces'
    ant = _sacar_ultima_oracion(res)
    i += 1
    cons, i = _leer_hasta(tokens, i, {'COMMA'})
    if not ant:
        raise ErrorSintaxis(f"«{palabra}» necesita algo antes, por ejemplo: «llueve, {palabra} me quedo».")
    if not cons:
        raise ErrorSintaxis(f"Después de «{palabra}» no hay nada.")
    if i < len(tokens) and tokens[i].tipo == 'COMMA':
        i += 1
    _emitir(res, ant, cons, tokens, i)
    return i


def reescribir_si_entonces(tokens: List[Token]) -> List[Token]:
    tokens = _quitar_conjuncion_inicial(_expandir_ni(tokens))
    res: List[Token] = []
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i]
        if t.tipo == 'EOF':
            break
        if t.tipo == 'IF':
            al_inicio = (not res) or res[-1].tipo in ('COMMA', 'LPAREN')
            if al_inicio:
                i = _condicional_directo(tokens, i, res)
            else:
                i = _condicional_invertido(tokens, i, res)
            continue
        if t.tipo == 'THEN':
            i = _conclusion_suelta(tokens, i, res)
            continue
        res.append(t)
        i += 1
    return res
