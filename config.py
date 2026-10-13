"""
Configuración central de TheHistoria.

Rutas y constantes. TheHistoria es un DEPARTAMENTO de CEO_Sergete: genera
historias de Instagram (9:16) y carruseles (4:5) para VARIOS PROYECTOS
independientes (cuentas o clientes de contenido). Lo de cada proyecto vive en
`proyectos/<id>/` (ver lib/proyectos.py); aquí solo van rutas y constantes comunes.

No duplica assets: el banco común de fondos es `TheEditor/superposiciones/` y el
b-roll propio de cada proyecto, `TheEditor/proyectos/<id>/recursos/broll/`.
"""
from __future__ import annotations
from pathlib import Path

# --- Rutas del propio proyecto ---
PROJECT_ROOT = Path(__file__).resolve().parent
FONTS_DIR = PROJECT_ROOT / "fonts"
OUT_DIR = PROJECT_ROOT / "salidas"            # salidas/<id>/<tanda | especiales_… | carrusel_…>/

# --- Proyectos (cuentas/clientes). Cada uno en proyectos/<id>/ (fuente de verdad):
# proyecto.json, estilo.json, especiales/ y planes/. `_plantilla` es la base de
# los nuevos (la copia CEO_Sergete/nuevo_proyecto.py sustituyendo <id> y <Nombre>).
PROYECTOS_DIR = PROJECT_ROOT / "proyectos"
PLANTILLA_ID = "_plantilla"
ETIQUETA_PROYECTO = "proyecto:{id}"          # etiqueta en viral_phrases.tags

# --- Proyectos hermanos (PruebasIA/) ---
PRUEBAS_IA = PROJECT_ROOT.parent
CEO_ROOT = PRUEBAS_IA / "CEO_Sergete"
EDITOR_ROOT = PRUEBAS_IA / "TheEditor"
DESCARGA_ROOT = PRUEBAS_IA / "TheDescarga"
HISTORICO_DIR = PRUEBAS_IA / "_Historico"     # _Historico/<id>/<video>/
CEO_PROYECTOS_JSON = CEO_ROOT / "proyectos.json"   # índice común (solo se lee)

# Política de RECURSOS de cada proyecto (fuente de verdad: TheEditor):
#   TheEditor/proyectos/<id>/proyecto.json → recursos {broll, internet, musica…}
# y su b-roll propio en TheEditor/proyectos/<id>/recursos/broll/ (opcional
# `_indice.json` para elegir por semántica). Se lee, no se duplica.
EDITOR_PROYECTOS_DIR = EDITOR_ROOT / "proyectos"
BROLL_POLITICAS = ("banco_comun", "propio", "ninguno")
# Si TheEditor aún no tiene la política del proyecto: la de `recursos_respaldo`
# del proyecto.json de TheHistoria y, si tampoco, la más restrictiva.
RECURSOS_RESPALDO = {"broll": "propio", "internet": False}

# Banco COMÚN de fondos (política `banco_comun`) = el MISMO b-roll que usa
# TheEditor (superposiciones/). Catalogado en Supabase `broll_assets` (filename +
# embedding + orientación), consultable por afinidad semántica con `match_broll`.
# Con `internet: false` se excluyen sus clips bajados de internet (prefijo pexels_).
FONDOS_DIR = EDITOR_ROOT / "superposiciones"
PREFIJOS_INTERNET = ("pexels_",)

# Política `ninguno` (o especiales sin vídeos): fondo liso del color de marca
# (`fondo_liso` del proyecto.json o `colores.fondo` del estilo.json).
FONDO_LISO_DEFECTO = "#14171f"

# Python del entorno con las dependencias ya instaladas (fastembed, httpx,
# Pillow, imageio-ffmpeg). Reutilizamos el .venv de TheEditor para NO instalar
# nada nuevo. Si algún día TheHistoria tiene su propio .venv, cambia esto.
EDITOR_VENV_PY = EDITOR_ROOT / ".venv" / "Scripts" / "python.exe"

# --- Lienzo de la historia (Instagram Story vertical) ---
STORY_W = 1080
STORY_H = 1920
STORY_FPS = 30
STORY_DURATION = 6.0          # segundos por historia (una frase)
FONDO_OSCURECER = 0.45        # scrim oscuro 0..1 sobre el fondo (legibilidad)

# Fracción de la ALTURA reservada ABAJO en las historias especiales para dejar
# sitio al botón/enlace de Instagram. El texto se centra en la zona superior
# [margen .. H*(1-RESERVA_INFERIOR_ESPECIAL)], no en la pantalla completa.
RESERVA_INFERIOR_ESPECIAL = 0.25

# --- Modelo de embeddings (EL MISMO con el que se indexó broll_assets) ---
EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Extensiones de vídeo válidas como fondo (igual que el pipeline del editor).
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"}

# Umbral mínimo de similitud para aceptar un fondo semántico (si no, azar).
FONDO_SIMILARITY_THRESHOLD = 0.28

# --- CARRUSELES de Instagram (tercera vía) ---
# Post del feed de 2-10 imágenes 4:5. El plan (proyectos/<id>/planes/<slug>.json)
# lo escribe el subagente y `carruseles.py` lo valida, lo renderiza y deja la
# carpeta de salida que lee TheCopy (contrato en README.md). El diseño de cada
# proyecto está en proyectos/<id>/estilo.json.
CARRUSEL_W = 1080
CARRUSEL_H = 1350
CARRUSEL_MIN_SLIDES = 2
CARRUSEL_MAX_SLIDES = 10
CARRUSEL_MAX_BYTES = 8 * 1024 * 1024     # límite de Instagram por imagen

# Auditor de estilo de TheCopy (paso opcional antes de renderizar). Se invoca
# como proceso aparte con su propio .venv: no se importa ni se copia su código.
THECOPY_ROOT = PRUEBAS_IA / "TheCopy"
THECOPY_PY = THECOPY_ROOT / ".venv" / "Scripts" / "python.exe"
THECOPY_CLI = THECOPY_ROOT / "copys.py"
