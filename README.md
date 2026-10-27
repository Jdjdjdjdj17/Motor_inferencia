# Motor de Tableaux Semántico (Árbol Semántico)

Aplicación en **Python** con interfaz gráfica en **Tkinter** para generar y visualizar el **árbol semántico (método de tableaux)** a partir de reglas escritas en **lenguaje natural español**.

## ¿De qué trata?

Este programa permite:

- Leer reglas y hechos en español (varias reglas a la vez).
- Identificar proposiciones simples (átomos) y asignarles letras (`p`, `q`, `r`, ...).
- Reconocer conectivos lógicos: `y`, `o`, `no`, `si... entonces`, `si y solo si`.
- Convertir el texto a fórmulas bien formadas con su respectiva precedencia y paréntesis.
- Generar el **árbol semántico por reglas α/β**.
- Mostrar las **reglas iniciales en el nodo raíz** y, en cada nodo, **solo lo que agrega su regla**, sin repetir las fórmulas anteriores.
- Marcar ramas posibles con `✓` y ramas descartadas con `✕`, numerando cada rama (`RAMA 1`, `RAMA 2`, ...).
- Listar **todas las ramas** con sus fórmulas acumuladas y el motivo de descarte o su modelo.
- Explicar **cómo se formó cada rama** paso a paso usando el nombre de los átomos, en una pestaña aparte.
- Mostrar las **ramas posibles** con sus respectivas asignaciones de valores (`p = V`, `q = F`, ...).
- Visualizar todo el árbol como un **grafo jerárquico**.

## Estructura del proyecto

```text
SE/
├── tableaux_app/
│   ├── core/        # Núcleo del motor (parser, fórmulas, átomos, tableaux)
│   ├── gui/         # Interfaz gráfica y renderizado del grafo
│   ├── tests/       # Pruebas
│   └── utils/       # Utilidades (normalización y persistencia de reglas)
├── run_tableaux.py  # Punto de entrada para lanzar la app
├── requirements.txt
├── .gitignore
└── README.md
```

### Componentes principales

| Archivo | Función |
| --- | --- |
| `core/lexico.py` | Tokenización por *longest-match* de conectivos en español (`si`, `entonces`, `y`, `o`, `no`, `si y solo si`, etc.). |
| `core/reescribir.py` | Reescribe `Si P, entonces Q` / `Si P entonces Q` a `P → Q`. |
| `core/atomos.py` | Diccionario atómico. Misma idea = mismo átomo. La negación `no` se representa como `¬q`, no como un átomo nuevo. |
| `core/parser.py` | Parser con precedencia (`¬ > ∧ > ∨ > → > ↔`) y agrupación de frases en un solo átomo. |
| `core/formulas.py` | Definición del AST (`Atom`, `Not`, `And`, `Or`, `Imp`, `Iff`) y conversión a string con paréntesis. |
| `core/tableau.py` | Motor de *tableaux*: aplica reglas **α** y **β**, marca fórmulas aplicadas, cierra ramas con átomo y negación (`✕`) y extrae modelos. |
| `gui/app.py` | Interfaz gráfica con Tkinter (fórmulas, tabla de átomos, modelos y grafo). |
| `gui/explicar.py` | Traduce fórmulas y ramas a lenguaje natural usando el nombre de los átomos; la explicación no muestra α/β. |
| `gui/render_grafo.py` | Renderizado jerárquico del árbol como grafo con NetworkX + Matplotlib. |
| `gui/gestor_reglas.py` | Ventana **Administrar reglas**: guarda, carga, renombra, duplica y elimina conjuntos de reglas con nombre. |
| `utils/sesion.py` | Persistencia de la última sesión y de los conjuntos con nombre; también exporta/importa en `.json` o `.txt`. |

## Requisitos

- Python 3.10+
- Sistema Linux/Windows/MacOS
- `python3-tk` (para Tkinter)

## Instalación

### 1) Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/NOMBRE_DEL_REPO.git
cd NOMBRE_DEL_REPO
```

### 2) Crear y activar entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/MacOS
# .venv\Scripts\activate   # Windows
```

### 3) Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Instalar Tkinter (si no lo tienes)

```bash
# Debian/Ubuntu/Linux Mint
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

Para comprobarlo:

```bash
python3 -c "import tkinter; print('Tkinter OK')"
```

## Uso

### Desde terminal

```bash
PYTHONPATH=. python3 run_tableaux.py
```

O con el entorno activado simplemente:

```bash
python run_tableaux.py
```

### Desde la interfaz gráfica

1. **Pegar reglas** - Escribe las reglas en lenguaje natural en el recuadro superior. Puedes poner varias, una por línea o separadas por punto.
2. **Generar Árbol** - Pulsa `Generar Árbol`.
3. **Revisar resultados** - El panel izquierdo tiene cuatro pestañas:
   - **Reglas y átomos**: fórmulas (`R1: ...`) con su lectura en palabras, tabla de átomos (`p = ...`) y el **camino correcto** (resumen de cada rama posible con su modelo).
   - **Ramas**: detalle técnico de **todas** las ramas (posibles y descartadas): camino, fórmulas acumuladas y cierre o modelo.
   - **Explicación**: **todas** las ramas explicadas paso a paso con los átomos, sus fórmulas en palabras, el motivo de descarte y el modelo natural.
   - **Modelos**: solo las ramas posibles, con la asignación en palabras y en letras.
4. **Ver el grafo** - En el panel derecho aparece el árbol semántico jerárquico.
   - El **nodo raíz** muestra las **reglas iniciales** completas.
   - Cada nodo muestra **solo lo que agrega su regla**, sin acumular las fórmulas anteriores.
   - **Verde con `✓`** = rama posible · **Rojo con `✕`** = rama descartada (sin las palabras "abierta/cerrada").
5. **Guardar imagen** - Con `Guardar Imagen` puedes exportar el grafo a `.png`, `.jpg` o `.pdf`.
6. **Administrar reglas** - Con `Administrar reglas` puedes guardar el conjunto actual con un nombre y **cargar, renombrar, duplicar o eliminar** los conjuntos guardados.

### Guardado de reglas

- Al cerrar la aplicación, las reglas se guardan automáticamente en `~/.tableaux_semantico/ultima_sesion.json`.
- Al abrirla de nuevo, se cargan esas reglas y el árbol se regenera automáticamente si son válidas.
- El botón **`Administrar reglas`** abre una ventana con todos los conjuntos guardados, su fecha y su cantidad de reglas.
- Cada conjunto se guarda como un `.json` independiente en `~/.tableaux_semantico/reglas/`.
- Los botones **`Guardar reglas`** y **`Abrir reglas`** siguen disponibles para exportar e importar archivos `.json` o `.txt`.
- Si las reglas guardadas tienen un error de sintaxis, el texto se conserva para que puedas corregirlo.

## Ejemplo de prueba

Copia esto en la interfaz para comprobarlo:

```text
Si es de día, entonces voy a trabajar.
Si llueve, entonces no voy a trabajar.
Es de día.
```

**Resultado esperado:**

- **Fórmulas:** `p → q`, `r → ¬q`, `p`
- **Átomos:** `p = es de día`, `q = voy a trabajar`, `r = llueve`
- **Ramas posibles:** 1
- **Modelo:** `p=V, q=V, r=F` (`sí es de día`, `sí voy a trabajar`, `no llueve`)
- **Árbol:** 2 ramas descartadas y 1 rama posible

## ¿Cómo funciona el motor?

1. **Normalización** - Convierte a minúsculas, quita tildes y normaliza espacios.
2. **Tokenización** - Busca conectivos con *longest-match* para no confundir `si` con `si y solo si`.
3. **Reescritura** - Transforma `si... entonces` a implicación `→`.
4. **Parser** - Agrupa las frases en proposiciones simples y construye el AST con precedencia correcta.
5. **Diccionario atómico** - Asigna letras únicas en orden de aparición. `¬q` reutiliza el átomo `q`.
6. **Tableaux α/β** - Expande las fórmulas siguiendo las reglas:
   - **Tipo α** (`∧`, `¬∨`, `¬→`, `¬¬`): Se añaden al mismo nodo (no bifurcan)
   - **Tipo β** (`∨`, `→`, `↔`, `¬∧`, `¬↔`): Bifurcan el árbol en dos ramas
7. **Cierre** - Si en una rama aparece un átomo y su negación, se cierra con `✕`.
8. **Modelos** - Al terminar, se extraen las asignaciones de las ramas posibles.

## Notas para desarrollo

- El `PYTHONPATH=.` es importante para importar correctamente `tableaux_app`.
- Las imágenes generadas (`.png`, `.jpg`, `.pdf`) están ignoradas por `.gitignore`.
- El entorno virtual `.venv/` también está ignorado, cada persona debe crearlo por su cuenta.
- `tkinter` no va en `requirements.txt`, debe instalararse con el gestor de paquetes del sistema.

## Autor

Proyecto para la materia de **Sistemas Expertos / Lógica**.

**Para el profe:** El motor se encuentra en `tableaux_app/core/`. Ahí está toda la lógica de parseo, diccionario atómico, y el motor de tableaux α/β. La interfaz es únicamente para visualización del árbol semántico.
# Motor-de-inferencia
