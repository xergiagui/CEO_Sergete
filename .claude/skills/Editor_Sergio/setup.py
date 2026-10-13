#!/usr/bin/env python3
"""
SETUP — Helpers para que el agent de Claude configure la skill desde 0.

El agent en chat:
1. Ejecuta `bash bootstrap.sh` → crea venv en ~/.viral-pipeline/venv/ con todas las deps
2. Usa `~/.viral-pipeline/venv/bin/python3` para todo lo siguiente
3. Pide al usuario las API keys + paths
4. Ajusta schema Airtable (vía API)
5. Sube foto a HeyGen
6. Guarda env en ~/.viral-pipeline/env.json

Sin watcher. El procesamiento es síncrono y se dispara con
`step3_process_pending(env)` de generate_from_link.py.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from pipeline_core import (
    ENV_PATH, HOME_DIR, PROJECT_ROOT, save_env, heygen_upload_photo, get_ffmpeg_exe,
)


# ============================================================
# Auto-detección de assets (foto + música) sin que el cliente
# tenga que pegar rutas absolutas. Búsqueda en orden:
#   1. <cwd>/viral-pipeline-assets/  (junto al proyecto Claude Code)
#   2. ~/.viral-pipeline/assets/     (fallback user-level)
# ============================================================
def find_assets_dir() -> Path | None:
    """Devuelve la primera carpeta de assets encontrada, o None."""
    candidates = [
        Path.cwd() / "viral-pipeline-assets",
        Path.home() / ".viral-pipeline" / "assets",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return None


def auto_detect_avatar_photo() -> Path | None:
    """Busca un archivo de avatar en la carpeta de assets.

    Prefiere `avatar.{jpg,png,webp}` exacto; si no, cualquier archivo
    cuyo nombre empiece por 'avatar' con extensión válida.
    """
    assets = find_assets_dir()
    if not assets:
        return None
    # 1. nombre exacto preferido
    for ext in ("jpg", "jpeg", "png", "webp"):
        f = assets / f"avatar.{ext}"
        if f.exists():
            return f
    # 2. cualquier "avatar*" (devuelve el primero alfabéticamente)
    matches = sorted(
        p for p in assets.glob("avatar*")
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    )
    return matches[0] if matches else None


def auto_detect_music_dir() -> Path | None:
    """Busca una carpeta `music/` dentro de assets con al menos 1 MP3."""
    assets = find_assets_dir()
    if not assets:
        return None
    music = assets / "music"
    if not music.is_dir():
        return None
    mp3s = list(music.glob("*.mp3")) + list(music.glob("*.MP3"))
    return music if mp3s else None


# Airtable FUERA del onboarding (queda dormido en pipeline_core por si se
# re-enchufa en el futuro). El flujo actual es 100% local.
REQUIRED_KEYS = [
    ("HEYGEN_API_KEY", "HeyGen API key (app.heygen.com → Space Settings → API)"),
    ("ELEVENLABS_API_KEY", "ElevenLabs API key (elevenlabs.io → Profile + API Keys)"),
    ("ELEVENLABS_VOICE_ID", "Voice ID clonada (Voice Lab → tu clon)"),
    ("AVATAR_NAME", "Nombre con el que etiquetas tu avatar (NO tiene que coincidir con el nombre de la voz de ElevenLabs). Ej: 'Marcos', 'María', 'Luis'..."),
    ("PEXELS_API_KEY", "API key de Pexels (gratis e instantánea en pexels.com/api). OBLIGATORIA — la skill la usa para intercalar B-roll en los huecos del avatar."),
    ("HEYGEN_ENGINE", "Engine HeyGen: 'avatar_v' (look subido por UI, mejor calidad, más caro, debe mirar a cámara) o 'avatar_iv' (talking_photo, más barato, menos calidad, vale aunque no mire a cámara)."),
]

REQUIRED_FILES = [
    ("MUSIC_DIR", "Ruta a una carpeta con MP3s"),
]

# Opcionales con default — el agent los pregunta pero acepta saltarlos
OPTIONAL_KEYS = [
    ("AUDIO_STYLE", "Estilo del audio — 'natural' (velocidad real, sin tocar silencios) o 'reel' (corte de silencios + 1.20x velocidad, ritmo más viral). Default: reel.", "reel"),
]


# Mapeo de AUDIO_STYLE a parámetros internos del audio processing
AUDIO_STYLE_PRESETS = {
    "natural": {"TTS_TEMPO": "1.00", "SILENCE_AGGRESSIVE": "false"},
    "reel":    {"TTS_TEMPO": "1.12", "SILENCE_AGGRESSIVE": "true"},
}


def apply_audio_style(env: dict) -> dict:
    """Expande AUDIO_STYLE del env a TTS_TEMPO + SILENCE_AGGRESSIVE concretos
    que el pipeline lee directamente. Llamar tras setup y antes de save_env.
    """
    style = (env.get("AUDIO_STYLE") or "reel").lower()
    preset = AUDIO_STYLE_PRESETS.get(style, AUDIO_STYLE_PRESETS["reel"])
    env.update(preset)
    return env


SCHEMA_FIELDS = [
    ("Link (referencia)", "url"),
    ("Status", "singleSelect:En cola,Procesando,Error,Publicado"),
    ("Texto", "multilineText"),
    ("Audio", "multipleAttachments"),
    ("Video Heygen", "multipleAttachments"),
    ("Video Editado", "multipleAttachments"),
    ("Pie de foto", "multilineText"),
    ("Avatar", "singleLineText"),
    ("Idioma", "singleSelect:Español,Inglés"),
]


def get_venv_python() -> Path:
    """Python con el que corre la skill: el .venv de TheEditor si existe (el de
    este equipo); si no, el venv de bootstrap. Raise si no hay ninguno."""
    cands = [PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
             PROJECT_ROOT / ".venv" / "bin" / "python",
             HOME_DIR / "venv" / "Scripts" / "python.exe",
             HOME_DIR / "venv" / "bin" / "python3"]
    for py in cands:
        if py.exists():
            return py
    raise RuntimeError(
        f"No hay venv ({PROJECT_ROOT / '.venv'} ni {HOME_DIR / 'venv'}). "
        f"Ejecuta primero bootstrap.py."
    )


# Claves sin las que la vía del avatar no puede arrancar (TTS + HeyGen). El
# setup solo se salta si están TODAS en env.json.
CLAVES_AVATAR = ["HEYGEN_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
                 "HEYGEN_ENGINE"]


def faltan_claves_setup(env: dict | None = None) -> list[str]:
    """Claves de HeyGen/ElevenLabs que faltan en env.json ([] = setup hecho).

    Incluye el ID del avatar según el engine (HEYGEN_LOOK_ID para avatar_v;
    HEYGEN_TALKING_PHOTO_ID o AVATAR_PHOTO para avatar_iv)."""
    import json
    if env is None:
        env = json.loads(ENV_PATH.read_text(encoding="utf-8")) if ENV_PATH.exists() else {}
    faltan = [k for k in CLAVES_AVATAR if not str(env.get(k) or "").strip()]
    engine = str(env.get("HEYGEN_ENGINE") or "").lower()
    if engine == "avatar_v" and not env.get("HEYGEN_LOOK_ID"):
        faltan.append("HEYGEN_LOOK_ID")
    elif engine == "avatar_iv" and not (env.get("HEYGEN_TALKING_PHOTO_ID") or env.get("AVATAR_PHOTO")):
        faltan.append("HEYGEN_TALKING_PHOTO_ID")
    return faltan


def validate_config(env: dict) -> list[str]:
    """Devuelve lista de errores. Vacía si todo OK."""
    errors = []
    for key, _ in REQUIRED_KEYS:
        if not env.get(key):
            errors.append(f"Falta: {key}")
    for key, _ in REQUIRED_FILES:
        path = env.get(key)
        if not path or not Path(path).exists():
            errors.append(f"Falta o no existe: {key} = {path}")
    music_dir = env.get("MUSIC_DIR")
    if music_dir and Path(music_dir).is_dir():
        mp3s = list(Path(music_dir).glob("*.mp3")) + list(Path(music_dir).glob("*.MP3"))
        if not mp3s:
            errors.append("MUSIC_DIR existe pero no contiene MP3s")

    # HeyGen: según el engine, exige el ID correcto
    engine = (env.get("HEYGEN_ENGINE") or "").lower()
    if engine not in ("avatar_v", "avatar_iv"):
        errors.append("HEYGEN_ENGINE debe ser 'avatar_v' o 'avatar_iv'")
    elif engine == "avatar_v" and not env.get("HEYGEN_LOOK_ID"):
        errors.append("Avatar V requiere HEYGEN_LOOK_ID (look subido por UI heygen.com)")
    elif engine == "avatar_iv" and not (
        env.get("HEYGEN_TALKING_PHOTO_ID") or env.get("AVATAR_PHOTO")
    ):
        errors.append(
            "Avatar IV requiere HEYGEN_TALKING_PHOTO_ID (look existente) "
            "o AVATAR_PHOTO (foto a subir)"
        )
    return errors


def verify_bootstrap() -> list[str]:
    """Verifica que bootstrap.sh fue ejecutado y el venv tiene libass.

    Si esta función devuelve problemas, el agent debe ejecutar
    `bash bootstrap.sh` antes de seguir.
    """
    problems = []
    venv_py = HOME_DIR / "venv" / "bin" / "python3"
    if not venv_py.exists():
        problems.append(
            f"venv no encontrado en {venv_py}. "
            f"Ejecuta: bash bootstrap.sh"
        )
        return problems

    # Importar deps con el python del venv
    for mod in ["httpx", "faster_whisper", "PIL", "imageio_ffmpeg", "yt_dlp"]:
        r = subprocess.run(
            [str(venv_py), "-c", f"import {mod}"],
            capture_output=True,
        )
        if r.returncode != 0:
            problems.append(f"Falta `{mod}` en el venv. Re-ejecuta bootstrap.sh")

    # libass disponible en el ffmpeg bundled
    try:
        ff = get_ffmpeg_exe()
        r = subprocess.run(
            [ff, "-hide_banner", "-filters"],
            capture_output=True, text=True, timeout=10,
        )
        has_ass = any(
            ln.split()[1:2] == ["ass"]
            for ln in r.stdout.splitlines() if ln.strip()
        )
        if not has_ass:
            problems.append(
                f"El ffmpeg bundled NO tiene libass. "
                f"Re-instala: $VENV/bin/pip install --force-reinstall imageio-ffmpeg"
            )
    except Exception as e:
        problems.append(f"No se pudo verificar ffmpeg: {e}")

    return problems


def upload_avatar_to_heygen(env: dict) -> str:
    """Sube la foto del avatar a HeyGen y guarda talking_photo_id en env."""
    photo_path = Path(env["AVATAR_PHOTO"])
    if not photo_path.exists():
        raise RuntimeError(f"Avatar photo no existe: {photo_path}")
    photo_id = heygen_upload_photo(photo_path, env["HEYGEN_API_KEY"])
    if not photo_id:
        raise RuntimeError("HeyGen no devolvió talking_photo_id")
    env["HEYGEN_TALKING_PHOTO_ID"] = photo_id
    save_env(env)
    return photo_id


def verify_look_avatar_v(look_id: str, api_key: str) -> bool:
    """True si el look_id soporta Avatar V (engine avatar_v).

    Si devuelve False justo tras subir la foto por UI, reintentar el MISMO
    id pasados unos minutos (HeyGen tarda en habilitar avatar_v).
    """
    from pipeline_core import heygen_look_supports_avatar_v
    return heygen_look_supports_avatar_v(look_id, api_key)


if __name__ == "__main__":
    if sys.argv[1:2] == ["faltan"]:
        # ¿Se puede saltar el setup? SETUP_OK o la lista de claves que faltan.
        f = faltan_claves_setup()
        print("SETUP_OK" if not f else "FALTAN: " + ", ".join(f))
        sys.exit(0 if not f else 1)
    print("Setup helpers para viral-pipeline v1.")
    print(f"Config se guardará en: {ENV_PATH}")
    print()
    print("Variables requeridas (las pide Claude en chat):")
    for k, desc in REQUIRED_KEYS + REQUIRED_FILES:
        print(f"  - {k}: {desc}")
    print()
    print("Para setup desde Claude Code:")
    print('  "monta el viral pipeline"')
    print()
    print("Claude:")
    print("  1. ejecuta bash bootstrap.sh (deps automáticas)")
    print("  2. te pide las keys + paths")
    print("  3. ajusta tu schema Airtable")
    print("  4. sube tu foto a HeyGen")
    print("  5. guarda config en ~/.viral-pipeline/env.json")
