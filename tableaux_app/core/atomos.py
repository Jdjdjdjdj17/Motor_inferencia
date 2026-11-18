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
    def __init__(self, reservadas: Dict[str, str] = None, siguiente: int = 0):
        """reservadas: {clave canónica -> letra} de un análisis anterior. Los átomos que siguen
        en uso conservan su letra; los que ya no aparecen en ninguna regla simplemente no se crean."""
        self.atomos: Dict[str, AtomInfo] = {}  # letra -> AtomInfo (solo los átomos en uso)
        self.key_a_id: Dict[str, str] = {}
        self.reservadas: Dict[str, str] = dict(reservadas or {})
        self.siguiente = siguiente

    def _letra(self, idx: int) -> str:
        letra = LETRAS[idx % len(LETRAS)]
        return letra if idx < len(LETRAS) else f"{letra}{idx // len(LETRAS)}"

    def _letra_libre(self) -> str:
        usadas = set(self.reservadas.values()) | set(self.atomos)
        while True:
            letra = self._letra(self.siguiente)
            self.siguiente += 1
            if letra not in usadas:
                return letra

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
        letra = self.reservadas.get(key_canon) or self._letra_libre()
        info = AtomInfo(id=letra, key=key_canon, texto=texto_frase.strip())
        self.atomos[letra] = info
        self.key_a_id[key_canon] = letra
        return letra

    def punto_de_control(self):
        """Guarda el estado para poder deshacer los átomos de una frase que falló."""
        return len(self.atomos), self.siguiente

    def restaurar(self, punto) -> None:
        n, siguiente = punto
        for letra in list(self.atomos)[n:]:
            info = self.atomos.pop(letra)
            self.key_a_id.pop(info.key, None)
        self.siguiente = siguiente

    def tiene_negacion(self, texto_frase: str) -> bool:
        s = a_minusculas_sin_tildes(texto_frase).strip()
        return s.startswith(('no ', 'nunca ', 'jamas ', 'ni '))

    def tabla(self) -> List[AtomInfo]:
        # en orden de aparición (el dict conserva el orden de inserción)
        return list(self.atomos.values())
