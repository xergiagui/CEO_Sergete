"""
Configuración central de TheCopy.

TheCopy es un DEPARTAMENTO de CEO_Sergete: genera el COPY y los HASHTAGS de
cada pieza aprobada (Reel = MP4, o carrusel = carpeta de slides) y deja
registrada la relación pieza ↔ copy ↔ hashtags (Excel por proyecto + un .txt
junto a cada MP4 o dentro de la carpeta del carrusel). Con el calendario, además,
le pone fecha y hora de publicación a lo aprobado.

El código es GENÉRICO: no sabe nada de ningún proyecto concreto. Todo lo
específico (tono, ofertas, CTA, hashtags, plataformas, carpetas) vive en
`proyectos/<id>/`. Un proyecto nuevo = copiar `proyectos/_plantilla/`.
"""
from __future__ import annotations
from pathlib import Path

# --- Rutas del propio proyecto ---
PROJECT_ROOT = Path(__file__).resolve().parent
PROYECTOS_DIR = PROJECT_ROOT / "proyectos"
PLANTILLA_DIR = PROYECTOS_DIR / "_plantilla"
TANDAS_DIR = PROJECT_ROOT / "tandas"

# --- Proyectos hermanos (PruebasIA/) ---
PRUEBAS_IA = PROJECT_ROOT.parent
EDITOR_ROOT = PRUEBAS_IA / "TheEditor"

# Dónde buscar los metadatos de cada clip (cortes.json + .srt de la
# transcripción). El nombre del clip final (finales/<nombre>.mp4) es el
# `nombre` de su entrada en cortes.json. Se mira primero lo que está en curso y
# luego lo archivado (al dar OK, las transcripciones pasan a _Historico).
FUENTES_METADATOS = [
    EDITOR_ROOT / "transcripciones",
    PRUEBAS_IA / "_Historico",
]

# Fragmento de transcripción que se pasa como contexto (caracteres máx.).
MAX_CHARS_TRANSCRIPCION = 1500

# Extensiones de vídeo que se consideran "clip" (Reel).
EXT_VIDEO = {".mp4", ".mov", ".m4v"}

# Formatos de pieza (columna Formato del registro). Un REEL es un MP4; un
# CARRUSEL es una CARPETA con `carrusel.json` + las slides (01.jpg … NN.jpg)
# que genera TheHistoria. Qué plataforma admite cada formato lo dice
# proyecto.json → plataformas.<p>.formatos (sin esa clave, solo "reel").
FORMATOS = {"reel": "Reel", "carrusel": "Carrusel"}
FORMATOS_PLURAL = {"reel": "Reels", "carrusel": "Carruseles"}
CARRUSEL_JSON = "carrusel.json"
EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
# Fórmulas de carrusel del contrato con TheHistoria (adaptadas de
# sergebulaev/instagram-skills, MIT). Una desconocida se acepta con aviso.
FORMULAS_CARRUSEL = {
    "IG5_lista": "Lista",
    "IG6_antes_despues": "Antes/después",
    "IG7_mitos": "Mitos",
    "IG8_metodo": "Método",
}

# Historias de IG (para el calendario): archivos que cuentan como historia.
EXT_HISTORIA = EXT_VIDEO | EXT_IMAGEN

# Días de la semana tal y como se escriben en proyecto.json → calendario.
DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
NOMBRES_DIA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# Estados posibles de una fila del registro.
ESTADOS = ["Pendiente", "Publicado", "Descartado", "No encontrado"]

# Rotación de hashtags: aviso si el conjunto de temáticos de un clip es igual al
# de alguno de los N últimos registrados en esa plataforma (o de otro clip de la
# misma tanda). Se puede cambiar por plataforma con hashtags.rotacion_ultimos.
ROTACION_ULTIMOS = 5
