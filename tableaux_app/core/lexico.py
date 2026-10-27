# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import List
from tableaux_app.utils.normalizar import a_minusculas_sin_tildes
from tableaux_app.core.errores import ErrorSintaxis

# Conectivos en español. Al comparar se normalizan (sin tildes) y se prueban
# del más largo al más corto (longest match), así "si y solo si" gana a "si".
OPERADORES_TEXTO = [
    ("si y solo si", "IFF"),
    ("si y solo cuando", "IFF"),
    ("equivale a", "IFF"),
    ("siempre que y solo cuando", "IFF"),
    ("si", "IF"),
    ("entonces", "THEN"),
    ("cuando", "IF"),
    ("en caso de que", "IF"),
    ("siempre que", "IF"),
    ("porque", "IF"),
    ("por lo tanto", "THEN"),
    ("luego", "THEN"),
    ("implica", "IMP"),
    ("y", "AND"),
    ("e", "AND"),
    ("además", "AND"),
    ("también", "AND"),
    ("pero", "AND"),
    ("o", "OR"),
    ("u", "OR"),
    ("no", "NOT"),
    ("nunca", "NOT"),
    ("jamás", "NOT"),
    ("ni", "NOT"),
]

_OPS = sorted(
    ((a_minusculas_sin_tildes(txt), tipo, txt) for txt, tipo in OPERADORES_TEXTO),
    key=lambda x: len(x[0]),
    reverse=True,
)

# Signos que no aportan nada a la lógica y se pueden ignorar sin perder información.
# Cualquier otro carácter raro (%, &, /, +...) lanza un error en vez de borrarse en silencio.
PUNTUACION_IGNORADA = set('¿?¡!"\'“”‘’«»:-–—`´')


@dataclass
class Token:
    tipo: str  # IF, THEN, IFF, IMP, AND, OR, NOT, LPAREN, RPAREN, COMMA, ATOM_TEXT, EOF
    valor: str
    texto_original: str = ""


def _agregar_separador(tokens: List[Token], simbolo: str) -> None:
    """Agrega un separador de reglas, sin duplicarlo ni ponerlo al inicio."""
    if tokens and tokens[-1].tipo != 'COMMA':
        tokens.append(Token('COMMA', ',', simbolo))


def tokenizar_conectores(texto: str) -> List[Token]:
    """
    Tokeniza buscando conectores por longest match.
    Lo demás se queda como ATOM_TEXT.
    Un salto de línea cuenta como separador de reglas (como un punto).
    """
    s = a_minusculas_sin_tildes(texto)
    tokens: List[Token] = []
    i = 0
    n = len(s)

    while i < n:
        c = s[i]
        if c == '\n':
            _agregar_separador(tokens, '\n')
            i += 1
            continue
        if c.isspace():
            i += 1
            continue
        if c == '(':
            tokens.append(Token('LPAREN', '(', '('))
            i += 1
            continue
        if c == ')':
            tokens.append(Token('RPAREN', ')', ')'))
            i += 1
            continue
        if c in ',;.':
            _agregar_separador(tokens, c)
            i += 1
            continue

        matched = False
        for op_norm, op_tipo, op_texto in _OPS:
            if s.startswith(op_norm, i):
                antes_ok = (i == 0 or not s[i - 1].isalnum())
                despues_idx = i + len(op_norm)
                despues_ok = (despues_idx >= n or not s[despues_idx].isalnum())
                if antes_ok and despues_ok:
                    tokens.append(Token(op_tipo, op_tipo, op_texto))
                    i += len(op_norm)
                    matched = True
                    break
        if matched:
            continue

        if c.isalnum() or c == '_':
            j = i
            while j < n and (s[j].isalnum() or s[j] == '_'):
                j += 1
            word = s[i:j]
            tokens.append(Token('ATOM_TEXT', word, word))
            i = j
            continue

        if c in PUNTUACION_IGNORADA:
            i += 1
            continue

        raise ErrorSintaxis(f"No reconozco el carácter «{c}». Escribe las reglas solo con palabras y conectivos.")

    tokens.append(Token('EOF', 'EOF', ''))
    return tokens
