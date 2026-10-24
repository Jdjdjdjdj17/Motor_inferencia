# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Dict, List
from tableaux_app.utils.normalizar import a_minusculas_sin_tildes, quitar_puntuacion_fuera

@dataclass
class AtomInfo:
    id: str  # p, q, r,...
    key: str  # clave canónica
    texto: str  # texto original

class DiccionarioAtomos:
    def __init__(self):
        self.atomos: Dict[str, AtomInfo] = {}  # key -> AtomInfo
        self.key_a_id: Dict[str, str] = {}
        self.siguiente = 0
        self.ids_letras = []
    
    def _letra(self, idx: int) -> str:
        # p,q,r,s,... hasta z (suficiente para ejercicios)
        if idx < 26:
            return chr(ord('p') + idx)
        # por si acaso
        base = chr(ord('p') + idx % 26)
        return base + str(idx // 26)
    
    def obtener_o_crear(self, texto_frase: str) -> str:
        if not texto_frase:
            return None
        s = a_minusculas_sin_tildes(texto_frase)
        s = quitar_puntuacion_fuera(s)
        s = s.strip()
        if not s:
            return None
        # quitar negaciones iniciales para clave canónica
        # detectar "no ..."
        key = s
        # normalizar "no voy..." -> quitar "no " para clave
        if key.startswith('no '):
            key_canon = key[3:].strip()
        elif key == 'no':
            key_canon = key
        else:
            key_canon = key
        if not key_canon:
            key_canon = key
        if key_canon in self.key_a_id:
            return self.key_a_id[key_canon]
        # crear nuevo
        letra = self._letra(self.siguiente)
        self.siguiente += 1
        info = AtomInfo(id=letra, key=key_canon, texto=texto_frase.strip())
        self.atomos[letra] = info
        self.key_a_id[key_canon] = letra
        return letra
    
    def tiene_negacion(self, texto_frase: str) -> bool:
        s = a_minusculas_sin_tildes(texto_frase).strip()
        if s.startswith('no ') or s.startswith('nunca ') or s.startswith('jamas ') or s.startswith('ni '):
            return True
        return False
    
    def tabla(self) -> List[AtomInfo]:
        # ordenar por letra
        items = list(self.atomos.values())
        items.sort(key=lambda x: ord(x.id[0]) if x.id else 0)
        return items
