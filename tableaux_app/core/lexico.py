# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import List, Tuple, Optional
from tableaux_app.utils.normalizar import a_minusculas_sin_tildes, quitar_tildes

# Operadores ordenados por longitud DESC (longest match)
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
    ("porque", "IF"),  # invertido más tarde
    ("por lo tanto", "THEN"),  # menos comun como separador, pero por si acaso
    ("luego", "THEN"),
    ("implica", "IMP"),
    ("y", "AND"),
    ("e", "AND"),
    ("ademas", "AND"),
    ("además", "AND"),
    ("tambien", "AND"),
    ("también", "AND"),
    ("pero", "AND"),
    ("o", "OR"),
    ("u", "OR"),
    ("no", "NOT"),
    ("nunca", "NOT"),
    ("jamás", "NOT"),
    ("jamás", "NOT"),
    ("ni", "NOT"),  # caso especial
]

@dataclass
class Token:
    tipo: str  # IF, THEN, IFF, IMP, AND, OR, NOT, LPAREN, RPAREN, COMMA, ATOM_TEXT, EOF
    valor: str
    texto_original: str = ""

def tokenizar_conectores(texto: str) -> List[Token]:
    """
    Tokeniza buscando conectores por longest match.
    Lo demás se queda como ATOM_TEXT.
    """
    s = a_minusculas_sin_tildes(texto)
    tokens: List[Token] = []
    i = 0
    n = len(s)
    
    # Crear lista ordenada por longitud
    ops = list(OPERADORES_TEXTO)
    ops_sorted = sorted(ops, key=lambda x: len(a_minusculas_sin_tildes(x[0])), reverse=True)
    
    while i < n:
        # Saltar espacios
        if s[i].isspace():
            i += 1
            continue
        # Puntuación
        if s[i] == '(':
            tokens.append(Token('LPAREN', '(', '('))
            i += 1
            continue
        if s[i] == ')':
            tokens.append(Token('RPAREN', ')', ')'))
            i += 1
            continue
        if s[i] == ',':
            tokens.append(Token('COMMA', ',', ','))
            i += 1
            continue
        if s[i] == ';':
            tokens.append(Token('COMMA', ',', ';'))  # tratar como separador
            i += 1
            continue
        if s[i] == '.':
            tokens.append(Token('COMMA', ',', '.'))
            i += 1
            continue
        
        # Intentar longest match de operador
        matched = False
        for op_texto, op_tipo in ops_sorted:
            op_norm = a_minusculas_sin_tildes(op_texto)
            if s.startswith(op_norm, i):
                # Verificar que es palabra completa (o empieza/termina apropiadamente)
                # Chequear límite anterior
                antes_ok = (i == 0 or not s[i-1].isalnum())
                despues_idx = i + len(op_norm)
                despues_ok = (despues_idx >= n or not s[despues_idx].isalnum())
                if antes_ok and despues_ok:
                    tokens.append(Token(op_tipo, op_tipo, op_texto))
                    i += len(op_norm)
                    matched = True
                    break
        if matched:
            continue
        
        # Leer palabra / átomo
        if s[i].isalnum() or s[i] == '_':
            j = i
            while j < n and (s[j].isalnum() or s[j] == '_'):
                j += 1
            word = s[i:j]
            tokens.append(Token('ATOM_TEXT', word, word))
            i = j
            continue
        
        i += 1  # skip unknown
    
    tokens.append(Token('EOF', 'EOF', ''))
    return tokens
