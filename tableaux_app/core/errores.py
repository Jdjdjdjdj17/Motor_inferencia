# -*- coding: utf-8 -*-


class ErrorSintaxis(ValueError):
    """Las reglas escritas no se pudieron interpretar.

    El mensaje está pensado para mostrarse tal cual al usuario.
    """


class ArbolDemasiadoGrande(ValueError):
    """El tableau creció más allá del límite permitido (demasiadas ramas por resolver)."""
