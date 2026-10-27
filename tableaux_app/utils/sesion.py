# -*- coding: utf-8 -*-
"""Persistencia de las reglas escritas por el usuario.

La última sesión se guarda automáticamente en:

    ~/.tableaux_semantico/ultima_sesion.json

Los conjuntos de reglas con nombre se guardan, uno por archivo, en:

    ~/.tableaux_semantico/reglas/

También se pueden exportar/importar reglas en `.json` o `.txt`.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

RUTA_SESION = Path.home() / ".tableaux_semantico" / "ultima_sesion.json"
DIRECTORIO_REGLAS = RUTA_SESION.parent / "reglas"


def _texto_desde_json(datos) -> str:
    """Acepta {"reglas": "..."}, una lista de líneas o un texto suelto."""
    if isinstance(datos, dict):
        reglas = datos.get("reglas", "")
    elif isinstance(datos, list):
        reglas = "\n".join(str(x) for x in datos)
    else:
        reglas = datos
    return reglas if isinstance(reglas, str) else str(reglas)


def cargar_ultima_sesion() -> Optional[str]:
    """Devuelve el texto de la última sesión, o None si no hay nada guardado."""
    if not RUTA_SESION.exists():
        return None
    try:
        with open(RUTA_SESION, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return _texto_desde_json(datos)


def cargar_ultima_sesion_nombre() -> str:
    """Devuelve el nombre del conjunto que estaba cargado en la última sesión."""
    if not RUTA_SESION.exists():
        return ""
    try:
        with open(RUTA_SESION, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ""
    if isinstance(datos, dict):
        nombre = datos.get("nombre", "")
        return nombre if isinstance(nombre, str) else ""
    return ""


def guardar_ultima_sesion(texto: str, nombre: str = "") -> bool:
    """Guarda el texto como última sesión. Devuelve True si se pudo guardar."""
    try:
        RUTA_SESION.parent.mkdir(parents=True, exist_ok=True)
        with open(RUTA_SESION, "w", encoding="utf-8") as f:
            json.dump(
                {"reglas": texto, "nombre": nombre},
                f, ensure_ascii=False, indent=2,
            )
        return True
    except OSError:
        return False


def guardar_archivo_reglas(ruta: str, texto: str) -> None:
    """Guarda las reglas en un `.json` o `.txt` según la extensión."""
    if ruta.lower().endswith(".json"):
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"reglas": texto}, f, ensure_ascii=False, indent=2)
    else:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)


def cargar_archivo_reglas(ruta: str) -> str:
    """Lee las reglas de un `.json` o `.txt` según la extensión."""
    if ruta.lower().endswith(".json"):
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return _texto_desde_json(datos)
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Conjuntos de reglas con nombre (ventana «Administrar reglas»)
# ---------------------------------------------------------------------------

def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(nombre: str) -> str:
    """Convierte un nombre en algo seguro para usar como archivo."""
    limpio = re.sub(r"[^\w\s-]", "", nombre.strip(), flags=re.UNICODE)
    limpio = re.sub(r"\s+", "_", limpio).strip("._-")
    return limpio[:80] or "reglas"


def _ruta_para(nombre: str, excluir: Optional[Path] = None) -> Path:
    base = _slug(nombre)
    ruta = DIRECTORIO_REGLAS / f"{base}.json"
    contador = 2
    while ruta.exists() and (excluir is None or ruta != excluir):
        ruta = DIRECTORIO_REGLAS / f"{base}_{contador}.json"
        contador += 1
    return ruta


def _leer_conjunto(ruta: Path) -> Optional[dict]:
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(datos, dict):
        return None
    texto = datos.get("reglas")
    if not isinstance(texto, str):
        return None
    numero = datos.get("num_reglas")
    if not isinstance(numero, int):
        numero = None
    return {
        "ruta": Path(ruta),
        "nombre": str(datos.get("nombre") or Path(ruta).stem),
        "reglas": texto,
        "creado": str(datos.get("creado") or ""),
        "modificado": str(datos.get("modificado") or ""),
        "num_reglas": numero,
    }


def _escribir_conjunto(ruta: Path, datos: dict) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    temporal.replace(ruta)


def listar_conjuntos() -> List[dict]:
    """Devuelve todos los conjuntos guardados, los más recientes primero."""
    if not DIRECTORIO_REGLAS.exists():
        return []
    conjuntos = []
    for ruta in DIRECTORIO_REGLAS.glob("*.json"):
        datos = _leer_conjunto(ruta)
        if datos is not None:
            conjuntos.append(datos)
    conjuntos.sort(
        key=lambda c: (c["modificado"] or "", c["nombre"].casefold()),
        reverse=True,
    )
    return conjuntos


def buscar_conjunto_por_nombre(nombre: str) -> Optional[dict]:
    """Busca un conjunto por nombre sin distinguir mayúsculas/minúsculas."""
    objetivo = nombre.strip().casefold()
    if not objetivo:
        return None
    for conjunto in listar_conjuntos():
        if conjunto["nombre"].casefold() == objetivo:
            return conjunto
    return None


def guardar_conjunto(nombre: str, texto: str, num_reglas: Optional[int] = None,
                     ruta: Optional[Path] = None) -> Path:
    """Crea o actualiza un conjunto con nombre y devuelve su ruta."""
    nombre = nombre.strip()
    ahora = _ahora()
    if ruta is None:
        ruta = _ruta_para(nombre)
        creado = ahora
    else:
        ruta = Path(ruta)
        anterior = _leer_conjunto(ruta)
        creado = anterior["creado"] if anterior and anterior["creado"] else ahora
    if num_reglas is None:
        num_reglas = len([linea for linea in texto.splitlines() if linea.strip()])
    datos = {
        "nombre": nombre,
        "reglas": texto,
        "creado": creado,
        "modificado": ahora,
        "num_reglas": num_reglas,
    }
    _escribir_conjunto(ruta, datos)
    return ruta


def renombrar_conjunto(ruta: Path, nuevo_nombre: str) -> Path:
    """Renombra un conjunto y devuelve su nueva ruta."""
    ruta = Path(ruta)
    datos = _leer_conjunto(ruta)
    if datos is None:
        raise FileNotFoundError(f"No se encontró el conjunto: {ruta}")
    nuevo_nombre = nuevo_nombre.strip()
    nueva_ruta = _ruta_para(nuevo_nombre, excluir=ruta)
    contenido = {
        "nombre": nuevo_nombre,
        "reglas": datos["reglas"],
        "creado": datos["creado"] or _ahora(),
        "modificado": _ahora(),
        "num_reglas": datos.get("num_reglas"),
    }
    _escribir_conjunto(nueva_ruta, contenido)
    if nueva_ruta != ruta:
        try:
            ruta.unlink()
        except FileNotFoundError:
            pass
    return nueva_ruta


def duplicar_conjunto(ruta: Path, nuevo_nombre: str) -> Path:
    """Duplica un conjunto con otro nombre y devuelve la ruta de la copia."""
    ruta = Path(ruta)
    datos = _leer_conjunto(ruta)
    if datos is None:
        raise FileNotFoundError(f"No se encontró el conjunto: {ruta}")
    nuevo_nombre = nuevo_nombre.strip()
    nueva_ruta = _ruta_para(nuevo_nombre)
    ahora = _ahora()
    contenido = {
        "nombre": nuevo_nombre,
        "reglas": datos["reglas"],
        "creado": ahora,
        "modificado": ahora,
        "num_reglas": datos.get("num_reglas"),
    }
    _escribir_conjunto(nueva_ruta, contenido)
    return nueva_ruta


def eliminar_conjunto(ruta: Path) -> None:
    """Elimina un conjunto guardado."""
    Path(ruta).unlink(missing_ok=True)
