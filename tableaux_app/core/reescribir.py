# -*- coding: utf-8 -*-
from typing import List
from tableaux_app.core.lexico import Token, tokenizar_conectores
from tableaux_app.utils.normalizar import a_minusculas_sin_tildes

def reescribir_si_entonces(tokens: List[Token]) -> List[Token]:
    """
    Reescribe "si P entonces Q" / "si P, Q" / "si P, entonces Q" a P IMP Q
    """
    res = []
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t.tipo == 'EOF':
            break
        if t.tipo == 'IF':
            i += 1  # saltar IF
            ant = []
            depth_paren = 0
            # extraer antecedente hasta THEN o COMMA (a nivel 0)
            while i < n:
                tt = tokens[i]
                if tt.tipo == 'LPAREN':
                    depth_paren += 1
                    ant.append(tt)
                    i += 1
                    continue
                if tt.tipo == 'RPAREN':
                    depth_paren -= 1
                    ant.append(tt)
                    i += 1
                    continue
                if depth_paren == 0 and tt.tipo == 'THEN':
                    i += 1  # saltar entonces
                    break
                if depth_paren == 0 and tt.tipo == 'COMMA':
                    i += 1  # saltar coma
                    # si viene entonces después, saltarlo
                    if i < n and tokens[i].tipo == 'THEN':
                        i += 1
                    break
                if depth_paren == 0 and tt.tipo == 'IF':
                    ant.append(tt)
                    i += 1
                    continue
                ant.append(tt)
                i += 1
            # extraer consecuente hasta separador de reglas
            cons = []
            depth_paren = 0
            # saltar THEN si quedó
            while i < n and depth_paren == 0 and tokens[i].tipo == 'THEN':
                i += 1
            while i < n:
                tt = tokens[i]
                if tt.tipo == 'EOF':
                    break
                if tt.tipo == 'LPAREN':
                    depth_paren += 1
                    cons.append(tt)
                    i += 1
                    continue
                if tt.tipo == 'RPAREN':
                    depth_paren -= 1
                    cons.append(tt)
                    i += 1
                    continue
                if depth_paren == 0 and tt.tipo == 'COMMA':
                    break
                if depth_paren == 0 and tt.tipo == 'IF':
                    # siguiente regla condicional - no consumir
                    break
                cons.append(tt)
                i += 1
            res.extend(ant)
            res.append(Token('IMP', 'IMP', '->'))
            res.extend(cons)
            res.append(Token('COMMA', ',', ','))
            continue
        res.append(t)
        i += 1
    return res
