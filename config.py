"""
Configuración central de TheHistoria.

Rutas y constantes. TheHistoria es un DEPARTAMENTO de CEO_Sergete: genera
historias de Instagram (9:16) a partir de las FRASES virales que TheEditor va
guardando en Supabase (tabla `viral_phrases`) y les pone un FONDO tomado del
MISMO catálogo de b-roll que usa TheEditor (`superposiciones/` + `broll_assets`).

No duplica assets: reutiliza `TheEditor/superposiciones/` como banco de fondos.
"""
from __future__ import annotations
from pathlib import Path

# --- Rutas del propio proyecto ---
PROJECT_ROOT = Path(__file__).resolve().parent
FONTS_DIR = PROJECT_ROOT / "fonts"
OUT_DIR = PROJECT_ROOT / "salidas"

# --- Proyectos hermanos (PruebasIA/) ---
PRUEBAS_IA = PROJECT_ROOT.parent
CEO_ROOT = PRUEBAS_IA / "CEO_Sergete"
EDITOR_ROOT = PRUEBAS_IA / "TheEditor"

# Banco de FONDOS = el MISMO b-roll que usa TheEditor (superposiciones/).
# Catalogado en Supabase `broll_assets` (filename + embedding + orientación),
# consultable por afinidad semántica con la RPC `match_broll`.
FONDOS_DIR = EDITOR_ROOT / "superposiciones"

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

# --- Modelo de embeddings (EL MISMO con el que se indexó broll_assets) ---
EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Extensiones de vídeo válidas como fondo (igual que el pipeline del editor).
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"}

# Umbral mínimo de similitud para aceptar un fondo semántico (si no, azar).
FONDO_SIMILARITY_THRESHOLD = 0.28
