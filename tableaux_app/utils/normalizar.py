# -*- coding: utf-8 -*-
import re
import unicodedata

def quitar_tildes(s: str) -> str:
    if not s:
        return s
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))

def normalizar_texto(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    # Normalizar espacios
    s = re.sub(r'\s+', ' ', s)
    return s

def a_minusculas_sin_tildes(s: str) -> str:
    return quitar_tildes(s.lower())

def quitar_puntuacion_fuera(s: str) -> str:
    # Quita puntuacion al final pero conserva puntos dentro? (raro) 
    # Solo quitar , ; : . ? ! al final
    s = re.sub(r'[\.,;:\?!]+$', '', s)
    s = re.sub(r'[\.,;:\?!]+', ' ', s)  # convertir otros a espacio
    return s
