# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Dict, List
from tableaux_app.utils.normalizar import a_minusculas_sin_tildes, quitar_puntuacion_fuera

# Letras en orden de aparición: p, q, r, ... z, a, b, ... o. Pasadas 26: p1, q1, ...
LETRAS = "pqrstuvwxyzabcdefghijklmno"


@dataclass
class AtomInfo:
    id: str  # p, q, r,...
    key: str  # clave canónica
    texto: str  # texto original


class DiccionarioAtomos:
    def __init__(self):
        self.atomos: Dict[str, AtomInfo] = {}  # letra -> AtomInfo
        self.key_a_id: Dict[str, str] = {}
        self.siguiente = 0

    def _letra(self, idx: int) -> str:
        letra = LETRAS[idx % len(LETRAS)]
        return letra if idx < len(LETRAS) else f"{letra}{idx // len(LETRAS)}"

    def obtener_o_crear(self, texto_frase: str) -> str:
        if not texto_frase:
            return None
        s = a_minusculas_sin_tildes(texto_frase)
        s = quitar_puntuacion_fuera(s)
        s = s.strip()
        if not s:
            return None
        key_canon = s
        if key_canon in self.key_a_id:
            return self.key_a_id[key_canon]
        letra = self._letra(self.siguiente)
        self.siguiente += 1
        info = AtomInfo(id=letra, key=key_canon, texto=texto_frase.strip())
        self.atomos[letra] = info
        self.key_a_id[key_canon] = letra
        return letra

    def tiene_negacion(self, texto_frase: str) -> bool:
        s = a_minusculas_sin_tildes(texto_frase).strip()
        return s.startswith(('no ', 'nunca ', 'jamas ', 'ni '))

    def tabla(self) -> List[AtomInfo]:
        # en orden de aparición (el dict conserva el orden de inserción)
        return list(self.atomos.values())
