"""
Configuración central de TheCopy.

TheCopy es un DEPARTAMENTO de CEO_Sergete: genera el COPY y los HASHTAGS de
cada pieza aprobada (Reel = MP4, o carrusel = carpeta de slides) y deja
registrada la relación pieza ↔ copy ↔ hashtags (Excel por proyecto + un .txt
junto a cada MP4 o dentro de la carpeta del carrusel). Con el calendario, además,
le pone fecha y hora de publicación a lo aprobado.

El código es GENÉRICO: no sabe nada de ningún proyecto concreto. La IDENTIDAD de
cada proyecto (cuenta, landing, voz, tono, emojis, palabras prohibidas) se lee del
índice del CEO (`CEO_Sergete/proyectos.json` → proyectos[].identidad); lo propio de
TheCopy (reglas del copy, ofertas, CTA, hashtags, plataformas, carpetas, calendario)
vive en `proyectos/<id>/`. Un proyecto nuevo = `copys.py nuevo-proyecto <id>` (copia
`proyectos/_plantilla/`). Las rutas de proyecto.json son relativas a PruebasIA/ y
admiten la plantilla `<id>` (se sustituye por el id del proyecto).
"""
from __future__ import annotations
from pathlib import Path

# --- Rutas del propio departamento ---
PROJECT_ROOT = Path(__file__).resolve().parent
PROYECTOS_DIR = PROJECT_ROOT / "proyectos"
PLANTILLA = "_plantilla"                      # no es un proyecto: no cuenta al elegir el proyecto
PLANTILLA_DIR = PROYECTOS_DIR / PLANTILLA
TANDAS_DIR = PROJECT_ROOT / "tandas"          # una subcarpeta por proyecto: tandas/<id>/

# --- Hermanos (PruebasIA/) ---
PRUEBAS_IA = PROJECT_ROOT.parent
CEO_ROOT = PRUEBAS_IA / "CEO_Sergete"
# Índice común de proyectos del CEO (solo se LEE): nombre, tipo y prefijo al crear un
# proyecto, y la IDENTIDAD de cada uno (fuente única: no se copia en proyecto.json).
INDICE_PROYECTOS = CEO_ROOT / "proyectos.json"

# Id de proyecto: minúsculas, sin espacios (letras, números, _ y -).
RE_ID_PROYECTO = r"[a-z0-9_][a-z0-9_-]*"

# Tipos de proyecto (los mismos en todos los departamentos):
#   largos   → vídeos largos cortados en clips por TheEditor: contexto = cortes.json + .srt
#   clipping → vídeos YA cortados que entrega el proyecto: contexto = textos/<clip>.txt (+ ganchos.json)
TIPOS = {
    "largos": "vídeos largos cortados en clips (contexto: cortes.json + .srt)",
    "clipping": "vídeos ya cortados que entrega el proyecto (contexto: textos/<clip>.txt)",
}

# Carpetas por defecto de un proyecto (relativas a PruebasIA/, `<id>` = id del proyecto).
# Cada proyecto las fija en su proyecto.json (carpetas.* y calendario.historias.carpeta);
# esto solo se usa si allí falta alguna. Las carpetas del CEO las crea el CEO, no TheCopy.
CARPETAS_POR_DEFECTO = {
    "pendiente": "CEO_Sergete/REVISADOS/<id>/1. pte Publicar",
    "publicado": "CEO_Sergete/REVISADOS/<id>/2. Publicados",
    "historias": "CEO_Sergete/HISTORIAS/<id>/1. Pte publicar",
}

# Dónde buscar el CONTEXTO de cada clip (proyecto.json → carpetas.contexto). Cada carpeta
# tiene una subcarpeta por vídeo con su cortes.json + .srt (largos) o textos/<clip>.txt
# (clipping). Primero lo que está en curso en TheEditor y luego lo archivado al dar OK.
CONTEXTO_POR_DEFECTO = [
    "TheEditor/proyectos/<id>/transcripciones",
    "_Historico/<id>",
]

# Fragmento de transcripción que se pasa como contexto en la tanda (caracteres máx.).
MAX_CHARS_TRANSCRIPCION = 1000

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
# Objetivo(s) para los que rinde cada fórmula. FUENTE ÚNICA: TheHistoria la lee con
# `copys.py campos --json --proyecto <id>` (contrato: no cambiar el formato).
FORMULA_OBJETIVOS = {
    "IG5_lista": ["guardados"],
    "IG6_antes_despues": ["guardados", "seguidores"],
    "IG7_mitos": ["compartidos"],
    "IG8_metodo": ["guardados"],
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
