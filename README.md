# Motor de Tableaux Semántico (Árbol Semántico)

Aplicación en **Python** con interfaz gráfica en **Tkinter** para generar y visualizar el **árbol semántico (método de tableaux)** a partir de reglas escritas en **lenguaje natural español**.

## ¿De qué trata?

Este programa permite:

- Leer reglas y hechos en español (varias reglas a la vez).
- Identificar proposiciones simples (átomos) y asignarles letras (`p`, `q`, `r`, ...).
- Reconocer conectivos lógicos: `y`, `o`, `no`, `si... entonces`, `si y solo si`.
- Convertir el texto a fórmulas bien formadas con su respectiva precedencia y paréntesis.
- Generar el **árbol semántico por reglas α/β**.
- Marcar ramas cerradas con `✕` y ramas abiertas con `✓`.
- Mostrar las **ramas abiertas** con sus respectivas asignaciones de valores (`p = V`, `q = F`, ...).
- Visualizar todo el árbol como un **grafo jerárquico**.

## Estructura del proyecto

```text
SE/
├── tableaux_app/
│   ├── core/        # Núcleo del motor (parser, fórmulas, átomos, tableaux)
│   ├── gui/         # Interfaz gráfica y renderizado del grafo
│   ├── tests/       # Pruebas
│   └── utils/       # Utilidades (normalización)
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
| `gui/render_grafo.py` | Renderizado jerárquico del árbol como grafo con NetworkX + Matplotlib. |

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
3. **Revisar resultados** - En el panel izquierdo verás: fórmulas (`R1: ...`), tabla de átomos (`p = ...`), y las ramas abiertas con sus modelos.
4. **Ver el grafo** - En el panel derecho aparece el árbol semántico jerárquico. 
   - **Verde** = Rama abierta (`✓ ABIERTA`)
   - **Rojo** = Rama cerrada (`✕ CERRADA`)
   - **✓ / ○** = Indican si la fórmula ya fue aplicada en ese nodo
5. **Guardar imagen** - Con `Guardar Imagen` puedes exportar el grafo a `.png`, `.jpg` o `.pdf`.

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
- **Ramas abiertas:** 1
- **Modelo:** `p=V, q=V, r=F`
- **Árbol:** 2 ramas cerradas y 1 rama abierta

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
8. **Modelos** - Al terminar, se extraen las asignaciones de las ramas abiertas.

## Notas para desarrollo

- El `PYTHONPATH=.` es importante para importar correctamente `tableaux_app`.
- Las imágenes generadas (`.png`, `.jpg`, `.pdf`) están ignoradas por `.gitignore`.
- El entorno virtual `.venv/` también está ignorado, cada persona debe crearlo por su cuenta.
- `tkinter` no va en `requirements.txt`, debe instalararse con el gestor de paquetes del sistema.

## Autor

Proyecto para la materia de **Sistemas Expertos / Lógica**.

**Para el profe:** El motor se encuentra en `tableaux_app/core/`. Ahí está toda la lógica de parseo, diccionario atómico, y el motor de tableaux α/β. La interfaz es únicamente para visualización del árbol semántico.
# Motor-de-inferencia
