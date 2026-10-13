#!/usr/bin/env python3
"""
Pipeline core — funciones compartidas viral-pipeline v1.

Sin watcher, sin paths hardcoded. Cada función es pura y portable.
El agent de Claude orquesta el flujo desde la conversación.

Pipeline completo por vídeo (de link a video editado publicado):
1. download_reel(url)                — yt-dlp
2. transcribe_video(path)            — faster-whisper large-v3
3. (Claude diseca beat-by-beat en chat)
4. (Claude genera nuevos guiones en chat)
5. tts_elevenlabs(text, voice_id)    — ElevenLabs eleven_v3
6. process_audio(mp3)                — atempo 1.15 + silenceremove
7. heygen_generate + heygen_wait     — Avatar IV talking_photo
8. burn_subs_and_music(video, music) — subs ASS karaoke + música + de-click
9. airtable_attach(record, video)    — upload vía 0x0.st + PATCH attachment
"""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import time
import re
from pathlib import Path
import httpx

# Config persistente entre conversaciones (NO en /tmp)
HOME_DIR = Path.home() / ".viral-pipeline"
HOME_DIR.mkdir(exist_ok=True)
ENV_PATH = HOME_DIR / "env.json"
COUNTER_PATH = HOME_DIR / "success_counter.txt"

# Workdir efímero para archivos grandes (vídeos, audios intermedios).
# Usa tempfile.gettempdir() para que funcione en Mac, Linux y Windows.
WORK_DIR = Path(tempfile.gettempdir()) / "viral_pipeline"
WORK_DIR.mkdir(exist_ok=True)

# Carpeta de fuentes de la skill (Montserrat) para libass
SKILL_DIR = Path(__file__).resolve().parent
FONTS_DIR = SKILL_DIR / "fonts"
# Raíz del proyecto TheEditor (skills/Editor_Sergio -> skills -> .claude -> TheEditor).
# Los assets locales (superposiciones/, musicas/) cuelgan de aquí, así que el
# pipeline funciona sea cual sea el cwd (p. ej. invocado desde CEO_Sergete).
PROJECT_ROOT = SKILL_DIR.parents[2]


# ============================================================
# GUARDA DE RED PARA RECURSOS (proyectos con `internet: false`)
#
# Un proyecto de TheEditor puede prohibir los recursos de internet (Pexels,
# imágenes libres, catálogo común `broll_assets`). No basta con no pedirlos: las
# funciones que los traen llaman a `_exigir_red_recursos()` y, si la red está
# bloqueada en este proceso, lanzan `RecursoExternoBloqueado` en vez de salir a
# internet. El bloqueo es de proceso y no tiene vuelta atrás (un proceso trabaja
# con un solo proyecto). Guardar frases en `viral_phrases` no es un recurso: no
# lo cubre esta guarda (se controla con `guardar_frases`).
# ============================================================
class RecursoExternoBloqueado(RuntimeError):
    """Se intentó traer un recurso de internet en un proyecto que lo prohíbe."""


_RED_RECURSOS = {"permitida": True, "motivo": ""}


def bloquear_red_recursos(motivo: str = "el proyecto no permite internet") -> None:
    """Prohíbe, para el resto del proceso, traer recursos de internet."""
    _RED_RECURSOS["permitida"] = False
    _RED_RECURSOS["motivo"] = motivo


def red_recursos_permitida() -> bool:
    return bool(_RED_RECURSOS["permitida"])


def _exigir_red_recursos(que: str) -> None:
    if not _RED_RECURSOS["permitida"]:
        raise RecursoExternoBloqueado(
            f"{que}: bloqueado, {_RED_RECURSOS['motivo'] or 'sin internet'}")


# ============================================================
# ENV (API keys + config)
# ============================================================
def load_env() -> dict:
    if not ENV_PATH.exists():
        raise RuntimeError(f"Falta {ENV_PATH}. Ejecuta primero el modo setup.")
    return json.loads(ENV_PATH.read_text())


def save_env(env: dict):
    ENV_PATH.write_text(json.dumps(env, indent=2, ensure_ascii=False))


# ============================================================
# FFMPEG resolver (portable, via imageio-ffmpeg con libass)
# ============================================================
def get_ffmpeg_exe() -> str:
    """Devuelve la ruta al ffmpeg bundled con libass.

    Usa imageio-ffmpeg que distribuye binarios cross-platform con libass
    compilado. Esto evita depender del ffmpeg del sistema (Homebrew/apt
    suele no incluir libass por defecto y los subs ASS fallan).
    """
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError(
            "Falta `imageio-ffmpeg`. Instala con: pip install imageio-ffmpeg"
        )


# ============================================================
# 1. DOWNLOAD
# ============================================================
DESCARGA_TOOLS = PROJECT_ROOT.parent / "TheDescarga" / "tools"


def _yt_dlp_cmd() -> list[str]:
    """Orden base de yt-dlp (+ --ffmpeg-location para muxar vídeo y audio).

    1) `../TheDescarga/tools/yt-dlp(.exe)` (el venv de TheEditor no trae yt_dlp);
    2) `python -m yt_dlp` si el módulo está instalado; 3) `yt-dlp` del PATH.
    """
    import importlib.util
    import shutil as _sh
    exe = DESCARGA_TOOLS / ("yt-dlp.exe" if sys.platform.startswith("win") else "yt-dlp")
    if exe.exists():
        cmd = [str(exe)]
    elif importlib.util.find_spec("yt_dlp") is not None:
        cmd = [sys.executable, "-m", "yt_dlp"]
    elif _sh.which("yt-dlp"):
        cmd = [_sh.which("yt-dlp")]
    else:
        raise RuntimeError(
            f"No hay yt-dlp: ni {exe}, ni el módulo yt_dlp, ni yt-dlp en el PATH.")
    ff_desc = DESCARGA_TOOLS / ("ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg")
    try:
        ff_loc = str(ff_desc) if ff_desc.exists() else get_ffmpeg_exe()
        cmd += ["--ffmpeg-location", ff_loc]
    except Exception:
        pass
    return cmd


def download_reel(url: str, out_dir: Path) -> Path:
    """Descarga reel forzando vídeo H.264 + audio AAC muxado a MP4.

    `-f mp4` a secas puede devolver un stream HEVC SÓLO-vídeo (sin audio) en
    TikTok/IG — y HEVC además le cuesta a PyAV. Aquí:
      -S codec:h264:aac → ordena prefiriendo vcodec avc1 + acodec aac
      -f "bv*+ba/b"     → mejor vídeo + mejor audio (garantiza pista de audio),
                          con fallback a mejor formato combinado
      --merge-output-format mp4 → muxa a un único source.mp4
    yt-dlp: el de TheDescarga (`../TheDescarga/tools/yt-dlp.exe`, el que se
    mantiene al día) si existe; si no, el módulo del Python actual o el del PATH.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "source.mp4"
    if out.exists():
        out.unlink()

    common = [
        *_yt_dlp_cmd(),
        "-S", "codec:h264:aac,res,br",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "--no-playlist", "--force-overwrites",
        "-o", str(out),
    ]
    # Estrategias en orden: primero SIN cookies (TikTok/YouTube y muchos IG van
    # así). Si falla — IG suele exigir login ("empty media response") — se
    # reintenta leyendo las cookies del NAVEGADOR DEL PROPIO USUARIO (que está
    # logueado en IG). Sin Apify ni tokens nuestros: cada cliente usa su sesión.
    import platform
    sysname = platform.system()
    if sysname == "Darwin":
        browsers = ["safari", "chrome", "brave", "firefox", "edge"]
    elif sysname == "Windows":
        browsers = ["chrome", "edge", "firefox", "brave"]
    else:
        browsers = ["chrome", "firefox", "brave", "chromium"]
    attempts = [common + [url]]
    attempts += [common + ["--cookies-from-browser", b, url] for b in browsers]

    last_err = ""
    for cmd in attempts:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
            return out
        last_err = (r.stderr or "")[-600:]
        if out.exists():
            out.unlink()

    raise RuntimeError(
        "No se pudo descargar el reel.\n"
        "  - Instagram: ábrelo en tu navegador estando LOGUEADO (yt-dlp usa "
        "esas cookies); si aun así falla, puede ser privado o restringido.\n"
        "  - TikTok / YouTube: suelen ir sin login.\n"
        f"  Detalle yt-dlp: {last_err}"
    )


# ============================================================
# 2. TRANSCRIBE
# ============================================================
def transcribe_video(video_path: Path, lang: str = None) -> tuple[str, str]:
    """Returns (full_text, detected_language)."""
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    segs, info = model.transcribe(str(video_path), language=lang, word_timestamps=False)
    text = " ".join(s.text.strip() for s in segs)
    return text, info.language


# ============================================================
# 5. TTS ELEVENLABS
# ============================================================
def tts_elevenlabs(text: str, voice_id: str, api_key: str, out_path: Path) -> Path:
    r = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_v3",
            "output_format": "mp3_44100_192",
        },
        timeout=300,
    )
    r.raise_for_status()
    out_path.write_bytes(r.content)
    return out_path


# ============================================================
# 6. PROCESS AUDIO (cortes sin click + atempo)
# ============================================================
# Velocidad/silencios por estilo de audio. FUENTE ÚNICA: el runtime deriva de
# AQUÍ (no del TTS_TEMPO congelado en env.json al hacer onboarding), así cambiar
# el ritmo propaga a TODOS los usuarios (envs viejos y nuevos) sin re-onboardear.
AUDIO_STYLE_PARAMS = {
    "natural": (1.00, False),
    "reel":    (1.12, True),
}


def audio_params_for_env(env: dict):
    """Devuelve (tempo, silence_aggressive) según env['AUDIO_STYLE'] (live)."""
    style = (env.get("AUDIO_STYLE") or "reel").lower()
    return AUDIO_STYLE_PARAMS.get(style, AUDIO_STYLE_PARAMS["reel"])


_SIL_START_RE = re.compile(r"silence_start: ([\d.]+)")
_SIL_END_RE = re.compile(r"silence_end: ([\d.]+)")


def process_audio(in_mp3: Path, out_mp3: Path, tempo: float = 1.12,
                  silence_aggressive: bool = True, noise_db: int = -24,
                  min_silence: float = 0.1, pad: float = 0.04,
                  fade: float = 0.006) -> Path:
    """Post-procesa TTS: corte de silencios SIN clicks + speed-up.

    Método (NO silenceremove, que mete clicks): silencedetect → segmentos de
    voz con `pad` a cada lado → micro-fade `afade` in/out de `fade`s por
    segmento (esto mata el click del empalme) → concat → atempo.

    tempo: ritmo del reel (1.12 default). noise_db: -24 corta bien (sube a
    -21/-18 para más agresivo; el TTS deja poco silencio puro).
    silence_aggressive=False → solo atempo, sin tocar silencios.
    """
    ff = get_ffmpeg_exe()

    def _only_tempo():
        subprocess.run(
            [ff, "-y", "-i", str(in_mp3), "-af", f"atempo={tempo}",
             "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3)],
            check=True, capture_output=True,
        )
        return out_mp3

    if not silence_aggressive:
        return _only_tempo()

    # 1. Detectar silencios
    det = subprocess.run(
        [ff, "-i", str(in_mp3), "-af",
         f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts = [float(x) for x in _SIL_START_RE.findall(det.stderr)]
    ends = [float(x) for x in _SIL_END_RE.findall(det.stderr)]
    dur = _get_duration(in_mp3, ff)

    # 2. Segmentos de voz (complemento de los silencios) con pad
    silences = list(zip(starts, ends))
    segs = []
    pos = 0.0
    for s_start, s_end in silences:
        if s_start > pos:
            segs.append((pos, min(s_start + pad, dur)))
        pos = max(s_end - pad, 0.0)
    if pos < dur:
        segs.append((pos, dur))
    if not segs:
        return _only_tempo()

    # 3. Por segmento: atrim + asetpts + micro-fade in/out (mata el click)
    parts = []
    for i, (s, e) in enumerate(segs):
        fo = max((e - s) - fade, 0.0)
        parts.append(
            f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={fade},afade=t=out:st={fo:.4f}:d={fade}[a{i}]"
        )
    n = len(segs)
    concat_in = "".join(f"[a{i}]" for i in range(n))
    parts.append(f"{concat_in}concat=n={n}:v=0:a=1[trimmed]")
    # 4. Ritmo
    parts.append(f"[trimmed]atempo={tempo}[a]")

    subprocess.run(
        [ff, "-y", "-i", str(in_mp3), "-filter_complex", ";".join(parts),
         "-map", "[a]", "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3)],
        check=True, capture_output=True,
    )
    return out_mp3


# ============================================================
# 7. HEYGEN AVATAR IV
# ============================================================
def heygen_generate(audio_path: Path, talking_photo_id: str, api_key: str) -> str:
    """Returns video_id. Pollea status hasta completed con heygen_wait."""
    ab = audio_path.read_bytes()
    r = httpx.post(
        "https://upload.heygen.com/v1/asset",
        headers={"X-Api-Key": api_key, "Content-Type": "audio/mpeg"},
        content=ab, timeout=180,
    )
    asset = r.json().get("data", {})
    body = {
        "caption": False, "title": "viral_pipeline",
        "video_inputs": [{
            "character": {
                "type": "talking_photo",
                "talking_photo_id": talking_photo_id,
                "use_avatar_iv_model": True,
                "talking_style": "stable",
                "super_resolution": True,
                "matting": False,
                "scale": 1, "offset": {"x": 0.0, "y": 0.0},
            },
            "voice": {
                "type": "audio",
                "voice_url": asset.get("url", ""),
                "audio_asset_id": asset.get("id", ""),
            },
        }],
        "dimension": {"width": 1080, "height": 1920},
    }
    r = httpx.post(
        "https://api.heygen.com/v2/video/generate",
        headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
        json=body, timeout=30,
    )
    return r.json().get("data", {}).get("video_id", "")


def heygen_wait(video_id: str, api_key: str, out_path: Path,
                max_attempts: int = 80, interval: int = 15) -> bool:
    for i in range(max_attempts):
        time.sleep(interval)
        try:
            s = httpx.get(
                f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
                headers={"X-Api-Key": api_key}, timeout=30,
            )
            if s.status_code != 200:
                continue
            d = s.json().get("data", {})
            status = d.get("status")
            if status == "completed":
                url = d.get("video_url")
                with httpx.stream("GET", url, timeout=300) as resp:
                    with open(out_path, "wb") as f:
                        for c in resp.iter_bytes():
                            f.write(c)
                return True
            if status in ("failed", "error"):
                return False
        except Exception:
            continue
    return False


def heygen_upload_photo(photo_path: Path, api_key: str) -> str:
    """Sube foto como talking_photo y devuelve talking_photo_id.

    Detecta el MIME por extensión. HeyGen rechaza si el Content-Type no
    coincide con los bytes reales (PNG enviado como image/jpeg → 401).
    """
    ext = photo_path.suffix.lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp"}.get(ext)
    if not mime:
        raise RuntimeError(f"Extensión no soportada: .{ext} (usa jpg/png/webp)")
    photo_bytes = photo_path.read_bytes()
    r = httpx.post(
        "https://upload.heygen.com/v1/talking_photo",
        headers={"X-Api-Key": api_key, "Content-Type": mime},
        content=photo_bytes, timeout=120,
    )
    data = r.json().get("data", {})
    return data.get("talking_photo_id") or data.get("id", "")


# ============================================================
# 7b. HEYGEN AVATAR V (engine v3) — look_id subido por la UI de heygen.com
#
# La foto SOLO califica como Avatar V si se sube por la web de heygen.com;
# por API no se puede crear. Por eso el setup pide el look_id ya existente.
# ============================================================
def heygen_look_supports_avatar_v(look_id: str, api_key: str) -> bool:
    """True si el look soporta el engine avatar_v.

    Tras subir la foto por UI puede tardar unos minutos en habilitar
    avatar_v; si da False recién subida, reintentar el MISMO id más tarde.
    """
    try:
        r = httpx.get(
            f"https://api.heygen.com/v3/avatars/looks/{look_id}",
            headers={"X-Api-Key": api_key}, timeout=30,
        )
        engines = r.json().get("data", {}).get("supported_api_engines", [])
        return "avatar_v" in engines
    except Exception:
        return False


def heygen_upload_audio_v3(audio_path: Path, api_key: str) -> str:
    """Sube audio como asset v3 (multipart). Devuelve asset_id."""
    with open(audio_path, "rb") as f:
        r = httpx.post(
            "https://api.heygen.com/v3/assets",
            headers={"x-api-key": api_key},
            files={"file": (audio_path.name, f, "audio/mpeg")},
            timeout=120,
        )
    r.raise_for_status()
    data = r.json()
    body = data.get("data", data)
    asset_id = body.get("asset_id") or body.get("id", "")
    if not asset_id:
        raise RuntimeError(f"HeyGen v3 /assets sin asset_id: {data}")
    return asset_id


def heygen_generate_v3(audio_path: Path, look_id: str, api_key: str) -> str:
    """Avatar V (engine avatar_v): sube audio v3 + POST /v3/videos. Devuelve video_id.

    El estado se pollea con heygen_wait_v3 (GET /v3/videos/{id}), distinto del IV.
    """
    asset_id = heygen_upload_audio_v3(audio_path, api_key)
    payload = {
        "type": "avatar",
        "avatar_id": look_id,
        "engine": {"type": "avatar_v"},
        "audio_asset_id": asset_id,
        "aspect_ratio": "9:16",
        "title": "viral_pipeline",
    }
    r = httpx.post(
        "https://api.heygen.com/v3/videos",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json=payload, timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    body = data.get("data", data)
    video_id = body.get("video_id") or body.get("id", "")
    if not video_id:
        raise RuntimeError(f"HeyGen v3 sin video_id: {data}")
    return video_id


def heygen_wait_v3(video_id: str, api_key: str, out_path: Path,
                   max_attempts: int = 60, interval: int = 25) -> bool:
    """Poll Avatar V por GET /v3/videos/{id} hasta completed; descarga el MP4."""
    for _ in range(max_attempts):
        time.sleep(interval)
        try:
            rs = httpx.get(f"https://api.heygen.com/v3/videos/{video_id}",
                           headers={"x-api-key": api_key}, timeout=30)
            if rs.status_code != 200:
                continue
            d = rs.json().get("data", rs.json())
            st = d.get("status", "")
            if st == "completed":
                url = d.get("video_url", "")
                if not url:
                    return False
                with httpx.stream("GET", url, timeout=300,
                                  follow_redirects=True) as resp:
                    with open(out_path, "wb") as f:
                        for c in resp.iter_bytes():
                            f.write(c)
                return True
            if st in ("failed", "error"):
                return False
        except Exception:
            continue
    return False


def heygen_generate_for_env(audio_path: Path, env: dict) -> str:
    """Dispatcher: lanza HeyGen según el engine configurado en env.

    env['HEYGEN_ENGINE']:
      - 'avatar_v'  → look_id subido por UI (env['HEYGEN_LOOK_ID']), mejor
                      calidad, más caro. Requiere mirar a cámara.
      - 'avatar_iv' → talking_photo (env['HEYGEN_TALKING_PHOTO_ID']), más
                      barato, menos calidad, vale aunque no mire a cámara.
    Default: avatar_iv (compat con configs antiguas).
    """
    engine = (env.get("HEYGEN_ENGINE") or "avatar_iv").lower()
    api_key = env["HEYGEN_API_KEY"]
    if engine == "avatar_v":
        look_id = env.get("HEYGEN_LOOK_ID") or env.get("HEYGEN_TALKING_PHOTO_ID", "")
        return heygen_generate_v3(audio_path, look_id, api_key)
    return heygen_generate(audio_path, env["HEYGEN_TALKING_PHOTO_ID"], api_key)


def heygen_wait_for_env(video_id: str, env: dict, out_path: Path) -> bool:
    """Poll según engine: Avatar V → /v3/videos/{id}; IV → /v1/video_status.get."""
    engine = (env.get("HEYGEN_ENGINE") or "avatar_iv").lower()
    if engine == "avatar_v":
        return heygen_wait_v3(video_id, env["HEYGEN_API_KEY"], out_path)
    return heygen_wait(video_id, env["HEYGEN_API_KEY"], out_path)


# ============================================================
# 8a. B-ROLL desde Pexels (opcional, solo si PEXELS_API_KEY en env)
# ============================================================
def fetch_pexels_clip(query: str, api_key: str, out_path: Path,
                      min_duration: int = 4, max_duration: int = 15) -> Path | None:
    """Descarga un clip vertical de Pexels que matchee `query`. Devuelve path o None."""
    _exigir_red_recursos("Pexels")
    r = httpx.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "orientation": "portrait", "per_page": 10},
        timeout=30,
    )
    if r.status_code != 200:
        return None
    videos = r.json().get("videos", [])
    # Filtrar por duración y elegir el mejor (vertical, calidad media)
    for v in videos:
        dur = v.get("duration", 0)
        if not (min_duration <= dur <= max_duration):
            continue
        # Buscar variante vertical con altura razonable
        files = sorted(v.get("video_files", []),
                       key=lambda f: abs(f.get("height", 0) - 1280))
        for vf in files:
            w, h = vf.get("width", 0), vf.get("height", 0)
            if h > w and h >= 720:  # vertical, mínima resolución
                url = vf.get("link", "")
                if not url:
                    continue
                with httpx.stream("GET", url, timeout=120) as resp:
                    with open(out_path, "wb") as f:
                        for c in resp.iter_bytes():
                            f.write(c)
                return out_path
    return None


_PROFANIDADES = {
    "joder", "jodido", "jodida", "jodidos", "jodidas", "jode", "joden",
    "mierda", "mierdas", "coño", "coños", "coñazo",
    "puta", "puto", "putas", "putos", "putada", "putadas",
    "gilipollas", "gilipollez", "gilipolleces", "capullo", "capullos",
    "cabron", "cabrón", "cabrones", "cabrona", "cabronas",
    "hostia", "hostias", "cojones", "cojón", "cojon",
    "follar", "folla", "follando", "polla", "pollas",
    "hijoputa", "hijaputa", "mamon", "mamón", "mamada", "mamadas",
}


def _mask_profanidad(word: str) -> str:
    """Enmascara palabrotas: mantiene 1ª letra + ***  (p.ej. 'jodida,' -> 'j***,')."""
    m = re.match(r"^(\W*)([^\W\d_]+)(\W*)$", word, re.UNICODE)
    if not m:
        return word
    pre, core, post = m.groups()
    if core.lower() in _PROFANIDADES:
        return f"{pre}{core[0]}***{post}"
    return word


# Fin de oración para RE-CAPITALIZAR subtítulos: la palabra termina en . ! ? …
# (admitiendo comillas/cierres de paréntesis tras el signo: p.ej.  fin.")
_SUBS_SENT_END_RE = re.compile(r"[.!?…][\"')\]»”’]*$")


def _cap_first_alpha(word: str) -> str:
    """Pone en MAYÚSCULA la primera letra alfabética, respetando signos de
    apertura iniciales (¿ ¡ « " ( …). Devuelve la palabra intacta si no tiene
    letras. Cubre acentos/ñ vía str.upper (Unicode)."""
    for i, ch in enumerate(word):
        if ch.isalpha():
            return word[:i] + ch.upper() + word[i + 1:]
    return word


def _download_image(url: str, out_path: Path, headers: dict) -> bool:
    """Descarga una imagen; True si es un archivo de imagen razonable (>8KB)."""
    _exigir_red_recursos("imagen de internet")
    try:
        with httpx.stream("GET", url, headers=headers,
                          timeout=60, follow_redirects=True) as resp:
            if resp.status_code != 200:
                return False
            ctype = resp.headers.get("content-type", "")
            if "image" not in ctype and not url.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".webp")):
                return False
            with open(out_path, "wb") as f:
                for c in resp.iter_bytes():
                    f.write(c)
        return out_path.exists() and out_path.stat().st_size > 8000
    except Exception:
        return False


def fetch_free_image(query: str, out_path: Path) -> Path | None:
    """Descarga UNA imagen libre (CC / dominio público) para el gancho inicial.

    Prioriza RELEVANCIA (se recorta a vertical luego, no se filtra por aspecto):
      1) Openverse — fotografías de uso comercial, ordenadas por relevancia.
      2) Wikimedia Commons — búsqueda de imágenes libres.
      3) Lorem Picsum — fallback aleatorio (sin búsqueda).
    Devuelve Path o None. Sin API key.
    """
    _exigir_red_recursos("imagen libre (Openverse/Wikimedia/Picsum)")
    headers = {"User-Agent": "viral-pipeline/1.0 (editor local)"}

    # 1) Openverse — por relevancia, solo fotografías, uso comercial
    try:
        r = httpx.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "license_type": "commercial",
                    "category": "photograph", "mature": "false", "page_size": 30},
            headers=headers, timeout=30,
        )
        if r.status_code == 200:
            for item in r.json().get("results", []):
                url = item.get("url") or ""
                if url and _download_image(url, out_path, headers):
                    return out_path
    except Exception:
        pass

    # 2) Wikimedia Commons — imágenes libres buscables
    try:
        s = httpx.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "format": "json", "generator": "search",
                    "gsrsearch": f"filetype:bitmap {query}", "gsrlimit": "15",
                    "gsrnamespace": "6", "prop": "imageinfo",
                    "iiprop": "url", "iiurlwidth": "1280"},
            headers=headers, timeout=30,
        )
        if s.status_code == 200:
            pages = (s.json().get("query") or {}).get("pages") or {}
            for p in pages.values():
                ii = (p.get("imageinfo") or [{}])[0]
                url = ii.get("thumburl") or ii.get("url") or ""
                if url and _download_image(url, out_path, headers):
                    return out_path
    except Exception:
        pass

    # 3) Fallback: Lorem Picsum (libre, aleatoria)
    if _download_image("https://picsum.photos/1080/1920", out_path, headers):
        return out_path
    return None


def apply_hook_video(video: Path, clip: Path, out_mp4: Path,
                     hook_dur: float = 2.5) -> Path:
    """Superpone un MINI-VIDEO (b-roll) a pantalla completa en los primeros
    `hook_dur` segundos como GANCHO inicial. El audio del clip base sigue intacto.
    """
    ff = get_ffmpeg_exe()
    filt = (
        f"[1:v]trim=0:{hook_dur},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,setsar=1[hk];"
        f"[0:v][hk]overlay=enable='between(t,0,{hook_dur})':x=0:y=0[v]"
    )
    subprocess.run([
        ff, "-y", "-i", str(video), "-i", str(clip),
        "-filter_complex", filt,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_mp4),
    ], check=True, capture_output=True)
    return out_mp4


def apply_hook_image(video: Path, image: Path, out_mp4: Path,
                     hook_dur: float = 1.8) -> Path:
    """Superpone una imagen a pantalla completa en los primeros `hook_dur`
    segundos del vídeo, como GANCHO inicial. El audio continúa intacto.
    """
    ff = get_ffmpeg_exe()
    filt = (
        f"[1:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,setsar=1,setpts=PTS-STARTPTS[img];"
        f"[0:v][img]overlay=enable='between(t,0,{hook_dur})':x=0:y=0[v]"
    )
    subprocess.run([
        ff, "-y", "-i", str(video), "-loop", "1", "-t", str(hook_dur), "-i", str(image),
        "-filter_complex", filt,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_mp4),
    ], check=True, capture_output=True)
    return out_mp4


def apply_broll_overlay(avatar_mp4: Path, broll_clips: list[Path],
                        avatar_duration: float, out_mp4: Path,
                        windows: list[tuple[float, float]] = None) -> Path:
    """Compone el avatar con cortes a B-roll a pantalla completa.

    Si `windows` (lista de (start, end) en segundos) se pasa, cada B-roll usa
    ESAS ventanas — sincronizadas con la voz (entran al arrancar una frase y
    salen en la pausa siguiente). Si es None, se reparten a intervalos
    regulares (~2.5s cada ~6s) como fallback. El audio del avatar continúa
    intacto (solo se sustituye el vídeo durante cada ventana; el shift de PTS
    evita el frame congelado en la entrada).
    """
    ff = get_ffmpeg_exe()
    n = len(broll_clips)
    if n == 0:
        # nada que hacer
        return avatar_mp4, []

    if windows is None:
        # Fallback legacy: primer corte a los 4s, espaciado regular
        seg_duration = 2.5
        interval = max(5.0, (avatar_duration - 6) / n)
        windows = []
        t = 4.0
        for i in range(n):
            end = min(t + seg_duration, avatar_duration - 1)
            if end - t < 1.5:
                break
            windows.append((t, end))
            t += interval
    else:
        windows = list(windows)

    # 1 clip por ventana (recorta al mínimo común de ambos)
    windows = windows[:len(broll_clips)]
    if not windows:
        return avatar_mp4, []

    # Construir filtergraph
    inputs = ["-i", str(avatar_mp4)]
    for clip in broll_clips[:len(windows)]:
        inputs += ["-i", str(clip)]

    chain = []
    for i, (start, end) in enumerate(windows, start=1):
        # Escalar + crop a 1080x1920. Recortar al duración necesaria y
        # SHIFTAR el pts al instante `start` del video principal —
        # sin el offset, el broll se congela en su frame 0 porque overlay
        # solo lo "muestra" cuando su pts ya está fuera de rango.
        seg_dur = end - start
        chain.append(
            f"[{i}:v]trim=0:{seg_dur},setpts=PTS-STARTPTS+{start}/TB,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920[br{i}]"
        )

    # Encadenar overlays
    prev = "[0:v]"
    for i, (start, end) in enumerate(windows, start=1):
        out_label = f"[v{i}]" if i < len(windows) else "[vout]"
        chain.append(
            f"{prev}[br{i}]overlay=enable='between(t,{start},{end})':x=0:y=0{out_label}"
        )
        prev = out_label

    filt = ";".join(chain)
    subprocess.run([
        ff, "-y", *inputs,
        "-filter_complex", filt,
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_mp4),
    ], check=True, capture_output=True)
    # Devuelve también los instantes de entrada de cada b-roll (para el SFX)
    return out_mp4, [start for (start, _end) in windows]


# ============================================================
# 8b. SINCRONIZACIÓN B-ROLL ↔ VOZ (frame-accurate, no por cronómetro)
# ============================================================
_SENT_END_RE = re.compile(r"[.!?…]$")


def _mk_phrase(group: list[dict]) -> dict:
    return {"start": group[0]["start"], "end": group[-1]["end"],
            "text": " ".join((g["word"] or "").strip() for g in group)}


def _phrases_from_words(words: list[dict], gap: float = 0.45) -> list[dict]:
    """Agrupa las palabras en FRASES por pausas de voz y puntuación de cierre.

    Se corta cuando el hueco entre dos palabras supera `gap` segundos o la
    palabra previa termina en . ! ? …  — así cada frase arranca en un inicio
    real de idea y termina en una pausa natural. Es la base para colocar el
    b-roll sincronizado con la voz en vez de a intervalos ciegos.
    """
    ws = [w for w in words
          if (w.get("word") or "").strip()
          and w.get("start") is not None and w.get("end") is not None]
    if not ws:
        return []
    phrases, cur = [], [ws[0]]
    for prev, w in zip(ws, ws[1:]):
        brk = (w["start"] - prev["end"] > gap) or \
              bool(_SENT_END_RE.search((prev["word"] or "").strip()))
        if brk:
            phrases.append(_mk_phrase(cur))
            cur = [w]
        else:
            cur.append(w)
    phrases.append(_mk_phrase(cur))
    return phrases


def _broll_windows_from_speech(phrases: list[dict], duration: float,
                               hook_dur: float = 2.5,
                               target_interval: float = 6.5,
                               min_seg: float = 1.6, max_seg: float = 3.2,
                               tail: float = 1.0) -> list[tuple[float, float]]:
    """Ventanas de b-roll ALINEADAS A LA VOZ, no a un cronómetro ciego.

    Recorre las frases y coloca un corte que ENTRA justo en el arranque de una
    frase y SALE al final de esa frase (la pausa siguiente), con una cadencia
    de ~`target_interval`s entre cortes. Nunca bajo el gancho inicial (primeros
    `hook_dur`s) ni en el último `tail`s del vídeo. Devuelve [] si no hay frases
    (el caller cae entonces a intervalos regulares).
    """
    windows: list[tuple[float, float]] = []
    if not phrases:
        return windows
    # permite el 1er corte poco después del gancho
    last_start = hook_dur - target_interval
    for ph in phrases:
        start = ph["start"]
        if start < hook_dur + 0.3:
            continue
        if start < last_start + target_interval:
            continue
        if start >= duration - tail - min_seg:
            break
        seg = min(max(ph["end"] - start, min_seg), max_seg)
        end = min(start + seg, duration - tail)
        if end - start < min_seg * 0.75:
            continue
        windows.append((round(start, 3), round(end, 3), ph.get("text", "")))
        last_start = start
    return windows


# ============================================================
# 8c. SELECCIÓN SEMÁNTICA DE B-ROLL (Supabase + embeddings locales)
#
# Casa cada frase hablada con el b-roll más afín del catálogo `broll_assets`
# (ver broll_assets.sql en TheLanding). Usa el MISMO modelo con el que se
# indexó: paraphrase-multilingual-MiniLM-L12-v2 (fastembed, 384d, local).
# Todo es best-effort: si falta fastembed, Supabase o las claves, devuelve
# None y el caller cae a selección local al azar.
# ============================================================
_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_embed_model = None
_broll_aviso_cache = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from fastembed import TextEmbedding
        _embed_model = TextEmbedding(model_name=_EMBED_MODEL_NAME)
    return _embed_model


def embed_text(text: str) -> list:
    """Embedding 384d de un texto con el modelo del catálogo (mismo que indexó)."""
    v = next(iter(_get_embed_model().embed([text])))
    return [float(x) for x in v]


def _supabase_headers(env: dict) -> dict:
    key = env.get("SUPABASE_ANON_KEY", "")
    return {"apikey": key, "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"}


def _broll_avisos(env: dict) -> set:
    """Filenames del catálogo con algún aviso (marca/persona/calidad) → evitar.
    Cacheado por proceso. Set vacío si Supabase no responde."""
    global _broll_aviso_cache
    _exigir_red_recursos("catálogo común broll_assets")
    if _broll_aviso_cache is not None:
        return _broll_aviso_cache
    out = set()
    url = (env or {}).get("SUPABASE_URL", "").rstrip("/")
    if url and env.get("SUPABASE_ANON_KEY"):
        try:
            r = httpx.get(f"{url}/rest/v1/broll_assets",
                          params={"select": "filename,logical_tags"},
                          headers=_supabase_headers(env), timeout=20)
            if r.status_code == 200:
                for row in r.json():
                    tags = row.get("logical_tags") or []
                    if any(str(t).startswith("aviso") for t in tags):
                        out.add(row["filename"])
        except Exception:
            pass
    _broll_aviso_cache = out
    return out


def broll_match_filename(phrase: str, env: dict, exclude=(),
                         want_orientation: str = None,
                         threshold: float = 0.30, k: int = 8):
    """Filename del b-roll más afín a `phrase` por encima de `threshold`,
    evitando `exclude` y los clips con aviso. None si nada supera el umbral o
    si no hay Supabase/embeddings disponibles (→ el caller usa azar)."""
    _exigir_red_recursos("catálogo común broll_assets (match_broll)")
    url = (env or {}).get("SUPABASE_URL", "").rstrip("/")
    if not url or not env.get("SUPABASE_ANON_KEY") or not (phrase or "").strip():
        return None
    try:
        body = {"query_embedding": embed_text(phrase), "match_count": k,
                "want_orientation": want_orientation}
        r = httpx.post(f"{url}/rest/v1/rpc/match_broll",
                       headers=_supabase_headers(env), json=body, timeout=20)
        if r.status_code != 200:
            return None
        avisos = _broll_avisos(env)
        for row in r.json():  # vienen ordenados por similitud desc
            fn = row.get("filename")
            if not fn or fn in exclude or fn in avisos:
                continue
            return fn if (row.get("similarity") or 0) >= threshold else None
    except Exception:
        return None
    return None


# ------------------------------------------------------------
# B-ROLL PROPIO DE UN PROYECTO: índice semántico LOCAL
# (proyectos/<id>/recursos/broll/_indice.json, lo genera indexar_broll.py)
#
#   {"modelo": <_EMBED_MODEL_NAME>, "dim": 384,
#    "archivos": [{"archivo": "<ruta relativa posix>", "descripcion": "...",
#                  "logical_tags": ["aviso-..."], "embedding": [384 floats]}]}
#
# Mismo modelo que el catálogo común, pero sin Supabase: nada sale a la red.
# Los archivos con una etiqueta `aviso*` no se usan.
# ------------------------------------------------------------
INDICE_BROLL = "_indice.json"


def _es_oculto(rel: Path) -> bool:
    """Partes que empiezan por '_' o '.' (índices, _frames/, descartes…)."""
    return any(part.startswith(("_", ".")) for part in rel.parts)


def list_overlays_recursive(overlays_dir: Path) -> dict:
    """{ruta_relativa_posix: Path} de los vídeos de una carpeta de b-roll propio
    (con subcarpetas; ignora lo que empieza por '_' o '.')."""
    d = Path(overlays_dir) if overlays_dir else None
    if not d or not d.is_dir():
        return {}
    out = {}
    for p in sorted(d.rglob("*")):
        if p.is_file() and p.suffix.lower() in _OVERLAY_VIDEO_EXTS:
            rel = p.relative_to(d)
            if not _es_oculto(rel):
                out[rel.as_posix()] = p
    return out


class IndiceBrollLocal:
    """Casación semántica frase → b-roll propio, 100 % local."""

    def __init__(self, path: Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.path = Path(path)
        self.modelo = data.get("modelo")
        self.vectores, self.avisos = {}, set()
        for e in data.get("archivos") or []:
            if not isinstance(e, dict) or not e.get("archivo"):
                continue
            rel = str(e["archivo"]).replace("\\", "/")
            tags = e.get("logical_tags") or []
            if any(str(t).startswith("aviso") for t in tags):
                self.avisos.add(rel)
                continue
            if isinstance(e.get("embedding"), list) and e["embedding"]:
                self.vectores[rel] = [float(x) for x in e["embedding"]]

    @classmethod
    def cargar(cls, path):
        """Índice o None (no existe, ilegible o hecho con otro modelo)."""
        if not path or not Path(path).exists():
            return None
        try:
            idx = cls(path)
        except Exception as e:
            print(f"  [broll] índice local ilegible ({e}): se usa azar")
            return None
        if idx.modelo and idx.modelo != _EMBED_MODEL_NAME:
            print(f"  [broll] índice local hecho con otro modelo ({idx.modelo}): se usa azar")
            return None
        return idx

    def match(self, phrase: str, exclude=(), threshold: float = 0.30):
        """Ruta relativa del b-roll más afín (≥ umbral, sin repetir) o None."""
        if not (phrase or "").strip() or not self.vectores:
            return None
        try:
            qv = embed_text(phrase)
        except Exception:
            return None
        best, best_sim = None, -1.0
        for rel, v in self.vectores.items():
            if rel in exclude:
                continue
            sim = _cosine(qv, v)
            if sim > best_sim:
                best, best_sim = rel, sim
        return best if best is not None and best_sim >= threshold else None


# ============================================================
# 8d. SELECCIÓN DE MÚSICA EN DOS PASOS (tipología por contenido + audio)
#
# `musicas/` está organizada en subcarpetas por tipología (mood). La elección
# es en dos pasos:
#   1) TIPOLOGÍA según el contenido del clip, con prioridad:
#      a) anotación `tipologia_musica` en cortes.json (match flexible de nombre)
#      b) inferencia por embeddings: se compara el texto del clip con un
#         descriptor rico de cada mood y se elige el de mayor similitud coseno
#      c) fallback a comodines curados/genéricos y, en último caso, random total
#   2) AUDIO por defecto: random dentro de la carpeta elegida.
# Reutiliza el modelo de embeddings del b-roll (fastembed, sin dependencias
# nuevas). Todo best-effort: nunca debe romper el render.
# ============================================================

# Descriptores ricos en español de cada MOOD (varios sinónimos por mood) para
# que el embedding case bien con el texto del clip. NEUTRA y DE LAS MEJORES NO
# son moods: son cajones comodín/curados → se excluyen de la inferencia.
_MUSIC_MOOD_DESCRIPTORS = {
    "alegre": ("música alegre feliz divertida positiva optimista jovial luminosa "
               "vibrante juguetona buen humor celebración fiesta sonrisa diversión "
               "energía positiva ligereza desenfadada simpática"),
    "energetica": ("música enérgica intensa potente con ritmo rápido y dinámico "
                   "acción adrenalina fuerza movimiento empuje pulso marcado beat "
                   "electrónica bailable entrenamiento deporte velocidad vigor"),
    "motivacion": ("música motivadora de superación esfuerzo disciplina constancia "
                   "perseverancia sacrificio trabajo duro lucha resiliencia levantarse "
                   "tras el fracaso lograr metas éxito crecer mejorar disciplina fuerza "
                   "de voluntad inspiración para no rendirse"),
    "nostalgia": ("música nostálgica melancólica sentimental emotiva de recuerdos y "
                  "añoranza del pasado tristeza suave memoria infancia tiempo perdido "
                  "reflexiva íntima agridulce evocadora"),
    "epica": ("música épica grandiosa cinematográfica heroica de triunfo gloria "
              "batalla apoteosis orquestal poderosa dramática monumental trascendental "
              "solemne impactante coros grandilocuente"),
    "inspiracion suaves": ("música inspiradora suave tranquila calmada relajante "
                           "delicada esperanzadora emotiva serena paz reflexión piano "
                           "cuerdas ambiental sutil ligera minimalista contemplativa"),
}

# Comodines (no-moods): orden de fallback cuando no hay tipología clara.
_MUSIC_FALLBACK_TYPS = ["de las mejores", "neutra"]

_music_mood_vec_cache = None


def _norm_typ(name: str) -> str:
    """Normaliza un nombre de tipología para match flexible.

    Quita el prefijo 'N. ', acentos y pasa a minúsculas/espacios colapsados.
    Así 'epica' == '15. ÉPICA' y 'motivacion' == '9. MOTIVACIÓN'.
    """
    import unicodedata
    t = unicodedata.normalize("NFKD", (name or "")).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"^\s*\d+\s*[.\-)]?\s*", "", t.lower())  # prefijo "9. " / "9 - "
    return re.sub(r"\s+", " ", t).strip()


def _music_typologies(music_dir: Path) -> dict:
    """Mapa {nombre_normalizado -> Path} de cada subcarpeta de `musicas/`."""
    out = {}
    d = Path(music_dir)
    if not d.is_dir():
        return out
    for sub in d.iterdir():
        if sub.is_dir():
            out[_norm_typ(sub.name)] = sub
    return out


def _list_music_files(folder) -> list:
    """MP3 dentro de una carpeta de tipología (sin recursión extra)."""
    if not folder:
        return []
    f = Path(folder)
    if not f.is_dir():
        return []
    return sorted(list(f.glob("*.mp3")) + list(f.glob("*.MP3")))


def _cosine(a, b) -> float:
    import math
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return s / (na * nb) if na and nb else 0.0


def _mood_descriptor_vecs():
    """Embeddings (cacheados) de los descriptores de cada mood. {} si falla."""
    global _music_mood_vec_cache
    if _music_mood_vec_cache is None:
        _music_mood_vec_cache = {}
        for norm, desc in _MUSIC_MOOD_DESCRIPTORS.items():
            try:
                _music_mood_vec_cache[norm] = embed_text(desc)
            except Exception:
                pass
    return _music_mood_vec_cache


def _infer_music_mood(text: str, available: dict):
    """(norm_typ, similitud) del mood más afín al texto, o (None, 0.0).

    Solo considera moods que EXISTEN como carpeta en disco (`available`).
    Excluye NEUTRA/DE LAS MEJORES por no ser moods. Best-effort: si no hay
    fastembed o algo falla, devuelve (None, 0.0)."""
    if not (text or "").strip():
        return None, 0.0
    try:
        qv = embed_text(text)
    except Exception:
        return None, 0.0
    dvecs = _mood_descriptor_vecs()
    best, best_sim = None, -1.0
    for norm, dv in dvecs.items():
        if norm not in available:  # el mood debe tener carpeta en disco
            continue
        sim = _cosine(qv, dv)
        if sim > best_sim:
            best_sim, best = sim, norm
    if best is None:
        return None, 0.0
    return best, best_sim


def select_music(music_dir: Path, typology: str = None, clip_text: str = None,
                 env: dict = None, rng=None):
    """Elige (music_path, log) en DOS pasos: tipología por contenido + audio.

    Prioridad de tipología:
      1) `typology` (anotación cortes.json) — match flexible por nombre.
      2) inferencia por embeddings sobre `clip_text` (moods; excluye comodines).
      3) fallback: comodines DE LAS MEJORES / NEUTRA y, en último caso, random
         entre TODAS las tipologías (y la raíz por compatibilidad).
    Dentro de la tipología elegida: audio por defecto (random). Si la carpeta
    está vacía, se pasa a la siguiente opción. Devuelve (None, motivo) si no hay
    ningún mp3 en absoluto. Nunca lanza por la selección en sí.

    `rng` (random.Random): con la semilla del clip la elección es reproducible
    (re-renderizar un clip da la misma música). None = azar sin semilla."""
    import random
    rng = rng or random.Random()
    typs = _music_typologies(music_dir)

    chosen, reason = None, None
    # 1) anotación explícita
    if typology and str(typology).strip():
        key = _norm_typ(typology)
        if key in typs:
            chosen, reason = key, f"anotación cortes.json '{typology}' -> {typs[key].name}"
        else:
            print(f"  [música] tipología anotada '{typology}' no existe en musicas/; se ignora")
    # 2) inferencia por embeddings
    if chosen is None and clip_text:
        inf, sim = _infer_music_mood(clip_text, typs)
        if inf:
            chosen, reason = inf, f"inferida por embeddings sim={sim:.3f} -> {typs[inf].name}"

    # orden de intentos: elegida -> comodines -> random total
    order = []
    if chosen:
        order.append((chosen, reason))
    for fb in _MUSIC_FALLBACK_TYPS:
        if fb in typs:
            order.append((fb, f"fallback comodín '{typs[fb].name}'"))

    for norm, why in order:
        files = _list_music_files(typs.get(norm))
        if files:
            music = rng.choice(files)
            return music, f"{why}; audio={music.name}"

    # último recurso: random entre TODAS las tipologías + raíz (compat. plano)
    allf = []
    for k in sorted(typs):
        allf += _list_music_files(typs[k])
    allf += _list_music_files(music_dir)
    if allf:
        music = rng.choice(allf)
        return music, f"fallback random total; audio={music.name}"
    return None, f"sin ningún mp3 en {music_dir}"


# ============================================================
# 8b. BANCO DE FRASES VIRALES (Supabase `viral_phrases`)
#
# Al analizar un viral (tras descargar + transcribir), el agente selecciona
# las frases más virales/interesantes del clip y las guarda aquí para MÁS
# ADELANTE crear historias de Instagram. De momento SOLO se almacenan.
# Tabla + policies: viral_phrases.sql (en TheLanding/supabase).
# Todo best-effort: si faltan Supabase o las claves, NO rompe el flujo.
# ============================================================
def _normalize_phrase(text: str) -> str:
    """Minúsculas, sin acentos ni puntuación, espacios colapsados — para dedup."""
    import unicodedata
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = t.encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _phrase_hash(text: str) -> str:
    import hashlib
    return hashlib.md5(_normalize_phrase(text).encode("utf-8")).hexdigest()


def _detect_platform(url: str) -> str:
    u = (url or "").lower()
    if "instagram." in u:
        return "instagram"
    if "tiktok." in u:
        return "tiktok"
    if "youtube." in u or "youtu.be" in u:
        return "youtube"
    return "otro" if u else None


def etiqueta_proyecto(proyecto: str) -> str:
    """Etiqueta con la que se marca el proyecto en `viral_phrases.tags`."""
    return f"proyecto:{proyecto}"


def store_viral_phrases(env: dict, phrases, source_url: str = None,
                        lang: str = None, avatar: str = None,
                        proyecto: str = None) -> dict:
    """Guarda (upsert por phrase_hash) las frases virales en Supabase.

    `phrases`: lista de str (solo el texto) o de dict con claves:
        phrase (obligatoria), category, angle, tags (list), virality (int 1..100),
        rationale. Las que aporte el agente al disecar el clip.
    `proyecto`: id del proyecto de TheEditor; añade la etiqueta
        `proyecto:<id>` a los `tags` de cada frase (sin quitar las demás).

    Devuelve {ok, stored, skipped, reason}. Best-effort: si no hay
    SUPABASE_URL/ANON_KEY, devuelve ok=False sin lanzar (no rompe el pipeline).
    Añade un `embedding` (384d) por frase si fastembed está disponible.
    """
    url = (env or {}).get("SUPABASE_URL", "").rstrip("/")
    if not url or not env.get("SUPABASE_ANON_KEY"):
        return {"ok": False, "stored": 0, "skipped": 0, "reason": "sin Supabase"}
    if not proyecto:
        print("  [frases] AVISO: sin proyecto -> las frases no llevan la etiqueta proyecto:<id>")

    platform = _detect_platform(source_url)
    rows, seen = [], set()
    for item in (phrases or []):
        if isinstance(item, str):
            item = {"phrase": item}
        phrase = (item.get("phrase") or "").strip()
        if not phrase:
            continue
        h = _phrase_hash(phrase)
        if h in seen:                      # dedup dentro del mismo lote
            continue
        seen.add(h)
        tags = [str(t) for t in (item.get("tags") or [])]
        if proyecto and etiqueta_proyecto(proyecto) not in tags:
            tags.append(etiqueta_proyecto(proyecto))
        row = {
            "phrase": phrase,
            "phrase_hash": h,
            "source_url": source_url,
            "source_platform": platform,
            "lang": lang,
            "avatar_name": avatar,
            "category": item.get("category"),
            "angle": item.get("angle"),
            "tags": tags,
            "virality": item.get("virality"),
            "rationale": item.get("rationale"),
        }
        try:                                # embedding opcional (best-effort)
            vec = embed_text(phrase)
            row["embedding"] = "[" + ",".join(str(x) for x in vec) + "]"
        except Exception:
            pass
        rows.append(row)

    if not rows:
        return {"ok": False, "stored": 0, "skipped": 0, "reason": "sin frases"}

    endpoint = f"{url}/rest/v1/viral_phrases?on_conflict=phrase_hash"
    headers = dict(_supabase_headers(env))
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    # Enviamos bytes UTF-8 EXPLÍCITOS (ensure_ascii=False + charset=utf-8) para
    # que ñ/á/é/í/ó/ú se guarden bien SIEMPRE, sin depender del cliente HTTP.
    headers["Content-Type"] = "application/json; charset=utf-8"
    payload = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    try:
        r = httpx.post(endpoint, headers=headers, content=payload, timeout=30)
        if r.status_code >= 400:
            return {"ok": False, "stored": 0, "skipped": len(rows),
                    "reason": f"HTTP {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "stored": 0, "skipped": len(rows),
                "reason": str(e)}
    return {"ok": True, "stored": len(rows), "skipped": 0, "reason": None}


# ============================================================
# 8. RENDER FINAL (subs ASS karaoke + música + de-click + B-roll opcional)
# ============================================================
# Exportación de las tres vías (regla de Sergio: 1080x1920, H.264, fps de la
# fuente, 8–12 Mb/s, AAC 48 kHz estéreo). Con CRF 18 un busto reescalado sale
# a ~6,5 Mb/s (por debajo del mínimo), así que se fija el bitrate: objetivo
# 10 Mb/s (mejor calidad que CRF 18 en ese material) y el VBV (maxrate/bufsize)
# impide pasar de 12 Mb/s en los tramos complejos.
VIDEO_ENC = ["-c:v", "libx264", "-preset", "medium", "-b:v", "10M",
             "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p"]
AUDIO_ENC = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def transcribe_words(video: Path, lang: str = "es") -> list[dict]:
    """Word-timestamps (faster-whisper large-v3) con palabrotas enmascaradas:
    lo que usan los subtítulos y la sincronía del b-roll."""
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    segs, _info = model.transcribe(str(video), language=lang, word_timestamps=True)
    return [{"word": _mask_profanidad(w.word.strip()), "start": w.start, "end": w.end}
            for s in segs for w in s.words]


def burn_subs_and_music(heygen_mp4: Path, music_dir: Path, out_mp4: Path,
                        lang: str = "es", env: dict = None,
                        broll_keywords: list[str] = None,
                        overlays_dir: Path = None,
                        hook_query: str = None,
                        music_typology: str = None,
                        clip_text: str = None,
                        words: list = None,
                        hook_text: str = None,
                        hook_text_dur: float = None,
                        recursos: dict = None,
                        seed: str = None) -> Path:
    """Render final: gancho + B-roll + música + de-click + subs ASS karaoke.

    `seed` (nombre del clip): toda elección al azar (música y b-roll) sale de
    `random.Random(seed)`, así que re-renderizar un clip da la misma música y el
    mismo b-roll y no cambia los demás. None = azar sin semilla.

    Exportación (las tres vías): H.264 1080x1920 a 10 Mb/s con VBV a 12
    (`VIDEO_ENC`, 8–12 Mb/s), AAC 48 kHz estéreo y la mezcla acabada en un
    limitador (`alimiter=limit=0.95`, pico < 0 dBFS).

    `recursos` = política de recursos del PROYECTO (ver `_politica_recursos`).
    None → comportamiento de siempre (banco común + internet: MongeMalo, vía 3).
    Con una política, el render solo usa lo que el proyecto permite:
      broll  banco_comun | propio (solo `overlays_dir`, índice local, sin
             repetir) | ninguno;
      musica banco_comun | propia (solo `music_dir`) | ninguna;
      internet False → ni Pexels, ni imágenes libres, ni catálogo común
             (además se bloquea la red de recursos del proceso).

    Gancho inicial: si `hook_query` no es None, descarga un MINI-VIDEO de Pexels
    (necesita `env['PEXELS_API_KEY']`) y lo superpone a pantalla completa los
    primeros ~2.5s como gancho. Si no hay key, cae a una imagen libre (Openverse).

    Gancho de TEXTO (opcional, DESACTIVADO por defecto): si `hook_text` trae
    texto, se quema en la franja superior desde el primer fotograma durante
    `hook_text_dur` s (salida suave de 0,2 s), encima del gancho visual y debajo
    de los subtítulos (ver `render_hook_text_png`). La vía del avatar no lo pasa,
    así que su render no cambia.

    B-roll a pantalla completa SINCRONIZADO con la voz: cada corte entra al
    arrancar una frase y sale en la pausa siguiente (se transcribe el avatar
    con word-timestamps y se derivan las ventanas); si no se detectan frases,
    cae a intervalos regulares. Prioriza SUPERPOSICIONES LOCALES (carpeta
    `superposiciones/`, o `env['OVERLAYS_DIR']`): coge vídeos locales al azar y
    los coloca en esas ventanas. Pexels queda como fallback solo si no hay
    superposiciones locales y `env['PEXELS_API_KEY']` + `broll_keywords` están
    definidos.
    """
    import random
    rng = random.Random(str(seed)) if seed else random.Random()
    ff = get_ffmpeg_exe()
    pol = _politica_recursos(recursos)
    legacy = pol["legacy"]
    # Red para RECURSOS: la del proyecto y, además, la guarda del proceso.
    net_ok = pol["internet"] and red_recursos_permitida()
    banco_broll = pol["broll"] == "banco_comun"

    # Selección de música en DOS PASOS: tipología (por contenido del clip) +
    # audio por defecto dentro de esa tipología. `music_dir` sigue siendo la
    # RAÍZ musicas/ (para _parse_music_offset y _find_broll_sfx en parent/sfx).
    music = None
    if pol["musica"] == "ninguna":
        print("  [música] el proyecto no lleva música")
    elif music_dir is None:
        if legacy or pol["musica"] == "banco_comun":
            raise RuntimeError("No hay carpeta de música")
        print("  [música] AVISO: el proyecto no tiene carpeta de música -> sin música")
    else:
        music, music_log = select_music(music_dir, typology=music_typology,
                                        clip_text=clip_text, env=env, rng=rng)
        if not music:
            if legacy or pol["musica"] == "banco_comun":
                raise RuntimeError(f"No hay MP3 en {music_dir} ({music_log})")
            print(f"  [música] AVISO: {music_log} -> sin música")
        else:
            print(f"  [música] {music_log}")

    # PASO 0: word-timestamps del avatar. El audio es idéntico en toda la
    # composición (hook y b-roll son overlays de vídeo: no tocan audio ni
    # duración), así que estos timings valen para (a) sincronizar el b-roll con
    # la voz y (b) los subtítulos — una sola transcripción para las dos cosas.
    base_video = heygen_mp4
    broll_starts = []  # instantes de entrada de cada b-roll (para el SFX)
    duration = _get_duration(heygen_mp4, ff)

    # Si el llamador ya transcribió (batch), reutilizamos sus `words` para no
    # correr whisper large-v3 dos veces por clip; si no, transcribimos aquí.
    if words is None:
        words = transcribe_words(heygen_mp4, lang=lang)

    # Ventanas de b-roll SINCRONIZADAS con la voz: (start, end, texto-de-frase).
    # Si no hay frases → intervalos (legacy).
    phrases = _phrases_from_words(words)
    windows_full = _broll_windows_from_speech(phrases, duration)

    # B-roll a pantalla completa. Prioridad: superposiciones LOCALES; Pexels
    # solo como fallback.
    clips = []
    windows = []
    if pol["broll"] == "propio":
        # SOLO el b-roll del proyecto: índice semántico local o azar SIN repetir
        # dentro del clip. Nunca el catálogo común ni Pexels.
        by_rel = list_overlays_recursive(overlays_dir) if overlays_dir else {}
        indice = IndiceBrollLocal.cargar(pol["broll_indice"])
        avisos = indice.avisos if indice else set()
        used = set()
        n_sem = 0
        if by_rel and windows_full:
            for (s, e, text) in windows_full:
                rel = indice.match(text, exclude=used) if (indice and text) else None
                if rel and rel in by_rel:
                    src = "sem-local"; n_sem += 1
                else:
                    pool = [r for r in by_rel if r not in used and r not in avisos]
                    if not pool:
                        print(f"  [broll] {s:.1f}-{e:.1f}s -> sin b-roll propio sin repetir (se omite)")
                        continue
                    rel = rng.choice(pool); src = "azar"
                used.add(rel)
                clips.append(by_rel[rel]); windows.append((s, e))
                print(f"  [broll] {s:.1f}-{e:.1f}s -> {rel} ({src})")
            print(f"  [broll] {len(clips)} cortes propios sinc. con la voz "
                  f"({n_sem} por índice local{'' if indice else '; sin índice'})")
        elif by_rel:
            n = max(1, int(duration // 6))
            pool = [r for r in by_rel if r not in avisos]
            rng.shuffle(pool)
            clips = [by_rel[r] for r in pool[:n]]
            print(f"  [broll] {len(clips)} b-roll propios (intervalos, sin frases): "
                  + ", ".join(c.name for c in clips))
        else:
            print(f"  [broll] el proyecto no tiene b-roll propio en {overlays_dir} -> sin b-roll")
        overlays = []
    elif pol["broll"] == "ninguno":
        print("  [broll] el proyecto no lleva b-roll")
        overlays = []
    else:
        if overlays_dir is None:
            overlays_dir = (env or {}).get("OVERLAYS_DIR") or (PROJECT_ROOT / "superposiciones")
        overlays_dir = Path(overlays_dir)
        overlays = _list_overlay_videos(overlays_dir)
        if overlays and not net_ok:
            # Banco común SIN internet: nada de catálogo (Supabase) ni de clips
            # que vinieron de internet (pexels_*); azar local sin repetir.
            overlays = [o for o in overlays if not o.name.lower().startswith("pexels_")]
            used = set()
            for (s, e, text) in windows_full:
                pool = [o for o in overlays if o.name not in used]
                if not pool:
                    break
                clip = rng.choice(pool); used.add(clip.name)
                clips.append(clip); windows.append((s, e))
                print(f"  [broll] {s:.1f}-{e:.1f}s -> {clip.name} (azar, sin internet)")
            overlays = []

    if overlays and windows_full:
        # SELECCIÓN SEMÁNTICA: por cada ventana (=frase) pedimos a Supabase
        # (match_broll) el b-roll más afín; si no supera umbral o no hay
        # Supabase, caemos a uno LOCAL al azar. Evitamos repetir clip y los
        # marcados 'aviso-*' (marca/persona/calidad).
        by_name = {p.name: p for p in overlays}
        avisos = _broll_avisos(env or {})
        used = set()
        n_sem = 0
        for (s, e, text) in windows_full:
            fn = broll_match_filename(text, env or {}, exclude=used) if (env and text) else None
            if fn and fn in by_name:
                clip = by_name[fn]; used.add(fn); src = "sem"; n_sem += 1
            else:
                pool = ([o for o in overlays if o.name not in used and o.name not in avisos]
                        or [o for o in overlays if o.name not in used] or overlays)
                clip = rng.choice(pool); used.add(clip.name); src = "azar"
            clips.append(clip); windows.append((s, e))
            print(f"  [broll] {s:.1f}-{e:.1f}s -> {clip.name} ({src})")
        print(f"  [broll] {len(clips)} cortes sinc. con la voz ({n_sem} por semántica)")
    elif overlays:
        # sin frases detectadas → intervalos regulares (legacy), clips al azar
        avisos = _broll_avisos(env or {})
        n = max(1, int(duration // 6))
        pool = [o for o in overlays if o.name not in avisos] or overlays
        rng.shuffle(pool)
        clips = (pool * (n // len(pool) + 1))[:n]
        print(f"  [broll] {len(clips)} superposiciones locales (intervalos, sin frases): "
              + ", ".join(c.name for c in clips))
    elif banco_broll and net_ok and not clips:
        pexels_key = (env or {}).get("PEXELS_API_KEY", "").strip()
        if pexels_key and broll_keywords:
            print(f"  [broll] (fallback Pexels) descargando {len(broll_keywords)} clips...")
            broll_dir = heygen_mp4.parent / "broll"
            broll_dir.mkdir(exist_ok=True)
            for i, kw in enumerate(broll_keywords, 1):
                clip = fetch_pexels_clip(kw, pexels_key, broll_dir / f"clip_{i}.mp4")
                if clip:
                    clips.append(clip)
                    print(f"    [{i}] '{kw}' → {clip.name}")
                else:
                    print(f"    [{i}] '{kw}' → SIN RESULTADO")

    if clips:
        base_video = heygen_mp4.parent / "with_broll.mp4"
        if windows:
            _, broll_starts = apply_broll_overlay(
                heygen_mp4, clips, duration, base_video, windows=windows)
        else:
            _, broll_starts = apply_broll_overlay(
                heygen_mp4, clips, duration, base_video)

    # PASO 0b: GANCHO — mini-video de Pexels a pantalla completa al inicio
    # (~2.5s). Si no hay PEXELS_API_KEY, cae a una imagen libre online.
    # Sin internet (política del proyecto o guarda del proceso) no hay gancho
    # visual: ni Pexels ni imágenes libres.
    if hook_query and not net_ok:
        print(f"  [hook] sin internet para recursos: se omite el gancho visual '{hook_query}'")
        hook_query = None
    if hook_query:
        hooked = heygen_mp4.parent / "with_hook.mp4"
        pexels_key = (env or {}).get("PEXELS_API_KEY", "").strip()
        done = False
        if pexels_key:
            hook_src = heygen_mp4.parent / "hook_src.mp4"
            clip = fetch_pexels_clip(hook_query, pexels_key, hook_src,
                                     min_duration=2, max_duration=30)
            if clip:
                print(f"  [hook] mini-video Pexels '{hook_query}' → {clip.name}")
                apply_hook_video(base_video, clip, hooked)
                base_video = hooked
                done = True
            else:
                print(f"  [hook] sin video Pexels para '{hook_query}'")
        if not done:
            img = fetch_free_image(hook_query, heygen_mp4.parent / "hook.jpg")
            if img:
                print(f"  [hook] (fallback) imagen libre '{hook_query}' → {img.name}")
                apply_hook_image(base_video, img, hooked)
                base_video = hooked
            else:
                print(f"  [hook] sin gancho disponible para '{hook_query}' (se omite)")

    # PASO 1: subtítulos ASS a partir de los word-timestamps ya calculados en
    # el PASO 0 (mismo timeline que la composición → evita una 2ª transcripción).
    ass_path = base_video.with_suffix(".ass")
    _generate_ass_karaoke(words, ass_path)

    music_offset = _parse_music_offset(music.name) if music else 0

    # SFX de transición: un click al ENTRAR cada b-roll (si hay sfx + ventanas).
    # Con política de proyecto, solo se busca en las carpetas que permite.
    if pol["sfx_dirs"] is None:
        sfx_path = _find_broll_sfx(music_dir) if music_dir is not None else None
    else:
        sfx_path = _find_sfx_in(pol["sfx_dirs"])
    sfx_chain = ""
    sfx_mix = ""
    extra_inputs = []
    use_sfx = bool(sfx_path and broll_starts)
    sfx_idx = 2 if music else 1          # índice de entrada del sfx en ffmpeg
    if use_sfx:
        nfx = len(broll_starts)
        splits = "".join(f"[k{i}]" for i in range(nfx))
        sfx_chain = f"[{sfx_idx}:a]asplit={nfx}{splits};"
        for i, t in enumerate(broll_starts):
            ms = int(max(t, 0.0) * 1000)
            sfx_chain += f"[k{i}]adelay={ms}|{ms},volume=0.8[sfx{i}];"
            sfx_mix += f"[sfx{i}]"
        extra_inputs = ["-i", str(sfx_path)]
        print(f"  [sfx] click en {nfx} entradas de b-roll ({sfx_path.name})")
    total_mix = (2 if music else 1) + (len(broll_starts) if use_sfx else 0)

    # volume=0.253 — música de fondo (~-12 dBFS)
    mus_chain = (f"[1:a]atrim=start={music_offset},asetpts=PTS-STARTPTS,volume=0.253[mus];"
                 if music else "")
    filt = (
        f"[0:a]aresample=async=1:first_pts=0,"
        f"adeclick=window=55:overlap=75:arorder=2:threshold=2:burst=2:method=add,"
        f"dynaudnorm=f=200:g=11[voz];"
        f"{mus_chain}"
        f"{sfx_chain}"
        f"[voz]{'[mus]' if music else ''}{sfx_mix}amix=inputs={total_mix}:duration=first:dropout_transition=0:"
        f"normalize=0,alimiter=limit=0.95:level=0[a]"
    )
    dur = _get_duration(base_video, ff)

    # Pass 1: mix audio
    pass1 = base_video.parent / f"{base_video.stem}_mix.mp4"
    music_inputs = ["-stream_loop", "-1", "-i", str(music)] if music else []
    subprocess.run([
        ff, "-y", "-i", str(base_video), *music_inputs,
        *extra_inputs,
        "-filter_complex", filt,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", *AUDIO_ENC,
        "-t", str(dur), "-movflags", "+faststart", str(pass1),
    ], check=True, capture_output=True)

    # Pass 2: burn subs ASS (requiere libass del binary bundled)
    # La ruta del filtro debe escaparse en Windows: '/' en vez de '\' y '\:'
    # para el ':' de la unidad (C:), o el parser del filtergraph falla.
    ass_ff = str(ass_path).replace("\\", "/").replace(":", "\\:")
    fonts_ff = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")
    vf_subs = f"ass='{ass_ff}':fontsdir='{fonts_ff}'"
    enc = [*VIDEO_ENC, "-c:a", "copy", "-movflags", "+faststart", str(out_mp4)]
    if hook_text and hook_text.strip():
        # Gancho de texto: PNG transparente superpuesto desde t=0, con fundido de
        # salida, y los subtítulos quemados ENCIMA (mismo pase: sin reencode extra).
        hook_png = base_video.parent / "hook_text.png"
        info = render_hook_text_png(hook_text, hook_png)
        hk_dur = max(0.5, min(float(hook_text_dur or HOOK_TEXT_DUR), dur - 0.05))
        fade_st = max(0.0, hk_dur - HOOK_TEXT_FADE)
        print(f"  [gancho texto] «{' / '.join(info['lines'])}» "
              f"({info['font_size']} px, 0-{hk_dur:.1f}s)")
        filt2 = (
            f"[1:v]format=rgba,fade=t=out:st={fade_st:.3f}:d={HOOK_TEXT_FADE}:alpha=1[hk];"
            f"[0:v][hk]overlay=x=0:y=0:eof_action=pass:format=auto[hv];"
            f"[hv]{vf_subs}[v]"
        )
        subprocess.run([
            ff, "-y", "-i", str(pass1),
            "-loop", "1", "-framerate", "30", "-t", f"{hk_dur:.3f}", "-i", str(hook_png),
            "-filter_complex", filt2,
            "-map", "[v]", "-map", "0:a", *enc,
        ], check=True, capture_output=True)
    else:
        subprocess.run([
            ff, "-y", "-i", str(pass1),
            "-vf", vf_subs, *enc,
        ], check=True, capture_output=True)
    pass1.unlink(missing_ok=True)
    return out_mp4


def _parse_music_offset(filename: str) -> int:
    m = re.search(r"segundo(\d+)", filename)
    return int(m.group(1)) if m else 0


_OVERLAY_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"}


def _list_overlay_videos(overlays_dir: Path) -> list[Path]:
    """Lista los vídeos de superposición (b-roll local) en `overlays_dir`.

    Solo vídeos (no imágenes): se usan como cortes a pantalla completa.
    Devuelve lista ordenada; vacía si la carpeta no existe o no tiene vídeos.
    """
    if not overlays_dir:
        return []
    d = Path(overlays_dir)
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir()
                  if p.is_file() and p.suffix.lower() in _OVERLAY_VIDEO_EXTS)


def _find_broll_sfx(music_dir: Path):
    """Localiza el SFX de click para las entradas de b-roll.

    Busca en <assets>/sfx/*.mp3|wav (assets = carpeta padre de music_dir),
    en <cwd>/viral-pipeline-assets/sfx/, o un click.* junto a music_dir.
    Devuelve Path o None.
    """
    cands = []
    for base in (music_dir.parent, Path.cwd() / "viral-pipeline-assets"):
        sfx_dir = base / "sfx"
        if sfx_dir.is_dir():
            cands += sorted(sfx_dir.glob("*.mp3")) + sorted(sfx_dir.glob("*.wav"))
        for name in ("click.mp3", "click.wav"):
            p = base / name
            if p.exists():
                cands.append(p)
    return cands[0] if cands else None


def _find_sfx_in(dirs) -> Path | None:
    """Primer click (*.mp3|*.wav) en las carpetas dadas (política de proyecto)."""
    for d in dirs or []:
        d = Path(d)
        if d.is_dir():
            cands = sorted(d.glob("*.mp3")) + sorted(d.glob("*.wav"))
            if cands:
                return cands[0]
    return None


def _politica_recursos(recursos: dict | None) -> dict:
    """Normaliza la política de recursos que pasa el proyecto al render.

    None → `legacy`: banco común + internet, exactamente como siempre.
    Claves: broll (banco_comun|propio|ninguno), musica (banco_comun|propia|
    ninguna), internet (bool), broll_indice (Path del _indice.json o None),
    sfx_dirs (None = búsqueda de siempre; lista = solo esas carpetas).
    Con internet=False bloquea además la red de recursos de todo el proceso.
    """
    pol = {"broll": "banco_comun", "musica": "banco_comun", "internet": True,
           "broll_indice": None, "sfx_dirs": None, "legacy": recursos is None}
    if recursos:
        for k in ("broll", "musica", "internet", "broll_indice", "sfx_dirs"):
            if k in recursos:
                pol[k] = recursos[k]
    if pol["broll"] not in ("banco_comun", "propio", "ninguno"):
        raise ValueError(f"política de b-roll no válida: {pol['broll']}")
    if pol["musica"] not in ("banco_comun", "propia", "ninguna"):
        raise ValueError(f"política de música no válida: {pol['musica']}")
    pol["internet"] = bool(pol["internet"])
    if not pol["internet"]:
        bloquear_red_recursos("el proyecto tiene internet=false")
    return pol


def _get_duration(file_path: Path, ff: str) -> float:
    """Devuelve duración en segundos parseando stderr de ffmpeg.

    Sustituye ffprobe (que no viene con imageio-ffmpeg bundled).
    ffmpeg sin -f output sale con error pero imprime metadata igualmente.
    """
    r = subprocess.run(
        [ff, "-i", str(file_path), "-hide_banner"],
        capture_output=True, text=True,
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise RuntimeError(
            f"No se pudo parsear duration de {file_path.name}: "
            f"{r.stderr[:300]}"
        )
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


# Fusión de números partidos por whisper. faster-whisper suele trocear un
# número con separador de miles/decimales en tokens distintos y SIN espacio de
# continuación (p.ej. "10.000" -> [" 10", ".000"]). Sin reunirlos, el número se
# rompe entre líneas/grupos del karaoke o queda con un espacio espurio ("10 .000").
# Estos regex detectan que dos tokens consecutivos forman UN número continuo:
#   - a termina en dígito y b empieza por separador+dígito  ("10" + ".000")
#   - a termina en dígito+separador y b empieza por dígito   ("10." + "000")
_NUM_TAIL = re.compile(r"\d$")            # a acaba en dígito
_NUM_HEAD_SEP = re.compile(r"^[.,]\d")    # b: .000 / ,5  (continuación de miles/decimal)
_NUM_TAIL_SEP = re.compile(r"\d[.,]$")    # a acaba en dígito+separador  ("10.")
_NUM_HEAD = re.compile(r"^\d")            # b empieza por dígito


def _merge_number_tokens(words):
    """Une tokens consecutivos que forman UN número con separadores internos.

    Sistémico: vale para "10.000", "1.500", "100.000", "3,5"… Nunca fusiona un
    punto de fin de frase real ("...año. Y...") porque exige dígitos a ambos
    lados del separador. Devuelve una nueva lista (no muta la de entrada);
    conserva start del 1º y end del último token fusionado."""
    out = []
    for w in words:
        cur = dict(w)
        if out:
            a = (out[-1].get("word") or "").strip()
            b = (cur.get("word") or "").strip()
            join = (_NUM_TAIL.search(a) and _NUM_HEAD_SEP.match(b)) or \
                   (_NUM_TAIL_SEP.search(a) and _NUM_HEAD.match(b))
            if join:
                prev = out[-1]
                prev["word"] = (prev.get("word") or "") + b  # sin espacio: es continuación
                prev["end"] = cur.get("end", prev.get("end"))
                continue
        out.append(cur)
    return out


def _subs_weak(word: str) -> bool:
    """¿Palabra débil (artículo, preposición, «que»…) que no debe cerrar un
    grupo de subtítulos? Con puntuación detrás (pausa o fin de frase) no lo es."""
    raw = (word or "").strip()
    if not raw or re.search(r"[.,;:!?…]$", raw):
        return False
    return raw.lower().strip("¿¡\"'«»()“”‘’") in _HOOK_WEAK


def _generate_ass_karaoke(words, ass_path: Path):
    """Subtítulos legibles y limpios (sin animación):
      - 1 sola línea, máximo 3 palabras, en minúsculas; el grupo se corta tras
        un fin de frase y nunca acaba en palabra débil (`_HOOK_WEAK`) si hay
        otra detrás (unidad de sentido).
      - Montserrat, blanco con RESEGUIDO NEGRO grueso + sombra suave.
      - Centrados horizontalmente y ubicados a la altura de la BARBILLA
        (ni tapan boca/ojos ni quedan al fondo de la pantalla).
      - Estáticos (aparecen/desaparecen, sin movimiento) -> mayor retención.
    """
    def fmt(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
        cs = int((s - int(s)) * 100); s = int(s)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    ws = [w for w in words if (w.get("word") or "").strip()]
    # Reunir números partidos por whisper ("10" + ".000" -> "10.000") ANTES de
    # agrupar: así el número queda en una sola unidad, nunca a caballo entre dos
    # líneas/grupos ni con un espacio espurio en medio.
    ws = _merge_number_tokens(ws)
    chunks = []
    i = 0
    # Estilo en minúsculas PERO respetando ortografía: la 1ª letra del texto y
    # la 1ª letra tras un punto (y por coherencia tras ? ! …) van en MAYÚSCULA.
    # `cap_next` persiste ENTRE chunks (el fin de oración puede caer al final de
    # un grupo y la mayúscula toca a la 1ª palabra del grupo siguiente).
    cap_next = True
    while i < len(ws):
        grp = ws[i:i + 3]  # máximo 3 palabras
        # cortar el grupo si hay un silencio grande entre palabras o si una
        # palabra cierra frase (. ? ! …): la frase siguiente empieza grupo nuevo
        cut = len(grp)
        for j in range(1, len(grp)):
            if (grp[j]["start"] - grp[j - 1]["end"] > 0.7
                    or _SUBS_SENT_END_RE.search((grp[j - 1]["word"] or "").strip())):
                cut = j
                break
        grp = grp[:cut]
        # unidad de sentido: el grupo no acaba en artículo/preposición/«que»…
        # (_HOOK_WEAK) si hay palabra después; esa palabra pasa al grupo siguiente
        while len(grp) > 1 and i + len(grp) < len(ws) and _subs_weak(grp[-1]["word"]):
            grp = grp[:-1]
        parts = []
        for w in grp:
            raw = (w["word"] or "").strip()
            disp = raw.lower()
            if cap_next:
                disp = _cap_first_alpha(disp)
            parts.append(disp)
            # ¿esta palabra cierra oración? -> la siguiente empieza en mayúscula
            if raw:
                cap_next = bool(_SUBS_SENT_END_RE.search(raw))
        text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        end = grp[-1]["end"]
        if end <= grp[0]["start"]:
            end = grp[0]["start"] + 0.3
        chunks.append({"start": grp[0]["start"], "end": end, "text": text})
        i += len(grp)

    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # Montserrat, blanco + reseguido negro grueso (Outline=6) + sombra (Shadow=3).
        # Alignment=2 (abajo-centro) + MarginV alto -> el texto SUBE hasta la barbilla.
        "Style: Default,Montserrat,76,&H00FFFFFF,&H000000FF,&H00000000,&HB4000000,1,0,0,0,100,100,0,0,1,6,3,2,80,80,640,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for c in chunks:
        lines.append(f"Dialogue: 0,{fmt(c['start'])},{fmt(c['end'])},Default,,0,0,0,,{c['text']}")
    ass_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# 8d. GANCHO DE TEXTO EN PANTALLA (primeros ~2.5 s)
#
# Texto corto que abre un bucle, visible desde el PRIMER fotograma (mucha gente
# ve los Reels sin sonido). Se dibuja con Pillow en un PNG transparente de
# 1080x1920 (misma Montserrat Bold que los subtítulos) y se superpone en el
# mismo pase en el que se queman los subtítulos, con salida suave. Mismas
# reglas de texto que los subtítulos: minúsculas + mayúscula al inicio y tras
# . ? ! …, palabrotas enmascaradas y números de miles sin partir.
# Opcional: burn_subs_and_music(hook_text=None) por defecto -> la vía del
# avatar (generate_from_link) no cambia.
# ============================================================
HOOK_TEXT_DUR = 2.5          # s en pantalla desde el primer fotograma
HOOK_TEXT_FADE = 0.2         # salida suave al final
_HOOK_W, _HOOK_H = 1080, 1920
_HOOK_TOP_FRAC = 0.125       # la caja empieza bajo el 12,5 % superior (barra de IG/TikTok)
_HOOK_SIDE = 120             # px libres a cada lado (aire en el borde derecho)
_HOOK_PAD_X, _HOOK_PAD_Y = 34, 26
_HOOK_MAX_FONT, _HOOK_MIN_FONT = 74, 50
_HOOK_LINE = 1.16            # interlineado (múltiplo del tamaño de letra)
_HOOK_SUBS_TOP = 1150        # los subtítulos ocupan ~1185-1280 px (MarginV 640): no bajar de aquí
# Palabras que no deben quedar colgando al final de la 1ª línea.
_HOOK_WEAK = {
    "a", "al", "ante", "con", "contra", "de", "del", "desde", "en", "entre",
    "hacia", "hasta", "para", "por", "sin", "sobre", "tras", "el", "la", "los",
    "las", "lo", "un", "una", "unos", "unas", "y", "e", "o", "u", "ni", "que",
    "se", "te", "me", "le", "les", "su", "sus", "tu", "tus", "mi", "mis", "no",
    "es", "más", "muy", "qué", "cómo",
}
_HOOK_OPEN_ONLY = re.compile(r"^[¿¡«\"'(\[]+$")
_HOOK_CLOSE_ONLY = re.compile(r"^[%€$£?!.,;:»\"')\]…]+$")


def format_hook_text(text: str) -> str:
    """Normaliza el texto del gancho con las MISMAS reglas que los subtítulos.

    Minúsculas, mayúscula en la 1ª letra y tras . ? ! …, palabrotas enmascaradas
    (`_mask_profanidad`) y números con separador reunidos ("10 .000" -> "10.000").
    """
    t = re.sub(r"\s+", " ", (text or "")).strip()
    t = re.sub(r"(?<=\d)\s+(?=[.,]\d)|(?<=\d[.,])\s+(?=\d)", "", t)
    out, cap_next = [], True
    for raw in t.split(" "):
        if not raw:
            continue
        disp = _mask_profanidad(raw).lower()
        if cap_next:
            disp = _cap_first_alpha(disp)
        out.append(disp)
        if any(ch.isalnum() for ch in raw) or _SUBS_SENT_END_RE.search(raw):
            cap_next = bool(_SUBS_SENT_END_RE.search(raw))
    return " ".join(out)


def _hook_tokens(disp: str) -> list[str]:
    """Unidades que NUNCA se parten entre líneas: cada palabra, con los signos
    sueltos pegados a su vecina ("1.500 €", "50 %", "¿ por" -> "¿por")."""
    toks: list[str] = []
    pend_open = ""
    for w in disp.split(" "):
        if _HOOK_OPEN_ONLY.match(w):
            pend_open += w
            continue
        w = pend_open + w
        pend_open = ""
        if toks and _HOOK_CLOSE_ONLY.match(w):
            toks[-1] = f"{toks[-1]} {w}" if w[0] in "%€$£" else toks[-1] + w
            continue
        toks.append(w)
    if pend_open:
        toks.append(pend_open)
    return toks


def _hook_font(size: int):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONTS_DIR / "Montserrat-Bold.ttf"), size)


def _hook_layout(tokens: list[str], max_w: int):
    """Elige tamaño de letra y reparto en líneas.

    Prioridad: la letra más grande posible en 1 línea o, si no cabe, en 2 líneas
    equilibradas (sin dejar artículo/preposición colgando al final de la 1ª).
    Si ni con la letra mínima cabe en 2 líneas, reparte en más (y se avisa).
    Devuelve (font, stroke, lines).
    """
    def width(font, s, stroke):
        l, _t, r, _b = font.getbbox(s, stroke_width=stroke)
        return r - l

    for size in range(_HOOK_MAX_FONT, _HOOK_MIN_FONT - 1, -2):
        font = _hook_font(size)
        stroke = max(3, round(size * 0.06))
        one = " ".join(tokens)
        if width(font, one, stroke) <= max_w:
            return font, stroke, [one]
        best = None
        for k in range(1, len(tokens)):
            l1, l2 = " ".join(tokens[:k]), " ".join(tokens[k:])
            w1, w2 = width(font, l1, stroke), width(font, l2, stroke)
            if max(w1, w2) > max_w:
                continue
            last = tokens[k - 1].lower().strip("¿¡,;:\"'«»()")
            cost = max(w1, w2) + (0.4 * max_w if last in _HOOK_WEAK else 0)
            # mejor partir donde ya hay pausa: fin de frase o coma/dos puntos
            if _SUBS_SENT_END_RE.search(tokens[k - 1]):
                cost -= 0.2 * max_w
            elif tokens[k - 1].endswith((",", ":", ";")):
                cost -= 0.1 * max_w
            if best is None or cost < best[0]:
                best = (cost, [l1, l2])
        if best:
            return font, stroke, best[1]

    # No cabe en 2 líneas ni con la letra mínima -> reparto voraz en N líneas.
    font = _hook_font(_HOOK_MIN_FONT)
    stroke = max(3, round(_HOOK_MIN_FONT * 0.06))
    lines, cur = [], ""
    for t in tokens:
        cand = f"{cur} {t}".strip()
        if cur and width(font, cand, stroke) > max_w:
            lines.append(cur)
            cur = t
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return font, stroke, lines


def render_hook_text_png(text: str, out_png: Path,
                         width: int = _HOOK_W, height: int = _HOOK_H) -> dict:
    """Dibuja el gancho de texto en un PNG transparente a tamaño de fotograma.

    Franja SUPERIOR dentro de la zona segura: la caja empieza bajo el 12,5 %
    superior (barra de IG/TikTok), deja 120 px a cada lado y queda muy por
    encima de los subtítulos (~1185-1280 px). Texto blanco Montserrat Bold con
    reseguido negro sobre una caja oscura semitransparente con esquinas
    redondeadas (legible sobre cualquier fondo en un móvil).
    Devuelve {"text", "lines", "font_size", "box"}.
    """
    from PIL import Image, ImageDraw

    disp = format_hook_text(text)
    if not disp:
        raise ValueError("gancho de texto vacío")
    max_w = width - 2 * _HOOK_SIDE - 2 * _HOOK_PAD_X
    font, stroke, lines = _hook_layout(_hook_tokens(disp), max_w)
    size = font.size

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = width // 2
    step = round(size * _HOOK_LINE)
    # Cajas de tinta de cada línea relativas a su línea base (anchor "ms").
    bbs = [draw.textbbox((cx, i * step), ln, font=font, anchor="ms", stroke_width=stroke)
           for i, ln in enumerate(lines)]
    # Altura de "cap" uniforme (no depende de si la línea lleva tildes o ¿):
    asc = font.getbbox("ÁÉÍ¿", anchor="ls")[1]      # negativo: por encima de la base
    desc = font.getbbox("gjpqy", anchor="ls")[3]
    ink_top = min(min(b[1] for b in bbs), asc - stroke)
    ink_bot = max(max(b[3] for b in bbs), (len(lines) - 1) * step + desc + stroke)
    ink_l = min(b[0] for b in bbs)
    ink_r = max(b[2] for b in bbs)

    box_top = round(height * _HOOK_TOP_FRAC)
    dy = box_top + _HOOK_PAD_Y - ink_top
    box = (ink_l - _HOOK_PAD_X, box_top, ink_r + _HOOK_PAD_X,
           ink_bot + dy + _HOOK_PAD_Y)
    draw.rounded_rectangle(box, radius=26, fill=(0, 0, 0, 150))
    for i, ln in enumerate(lines):
        draw.text((cx, i * step + dy), ln, font=font, anchor="ms",
                  fill=(255, 255, 255, 255), stroke_width=stroke,
                  stroke_fill=(0, 0, 0, 255))
    img.save(out_png)

    if box[3] > _HOOK_SUBS_TOP:
        print(f"  [gancho texto] AVISO: la caja baja hasta y={box[3]} y podría tocar los subtítulos")
    if len(lines) > 2:
        print(f"  [gancho texto] AVISO: texto largo ({len(disp)} car.) -> {len(lines)} líneas; "
              f"conviene acortarlo (máx. 2 líneas, ~45 car.)")
    return {"text": disp, "lines": lines, "font_size": size, "box": box}


# ============================================================
# 9. AIRTABLE — PATCH fields + upload attachments (vía 0x0.st)
# ============================================================
def airtable_patch(record_id: str, fields: dict, env: dict) -> int:
    """PATCH a un record (Status, Texto, Pie de foto, etc.)."""
    url = (f"https://api.airtable.com/v0/{env['AIRTABLE_BASE_ID']}/"
           f"{env['AIRTABLE_TABLE_ID']}/{record_id}")
    r = httpx.patch(
        url,
        headers={"Authorization": f"Bearer {env['AIRTABLE_PAT']}",
                 "Content-Type": "application/json"},
        json={"fields": fields}, timeout=60,
    )
    return r.status_code


def airtable_create(fields: dict, env: dict) -> str:
    """Crea un record nuevo y devuelve su record_id."""
    url = (f"https://api.airtable.com/v0/{env['AIRTABLE_BASE_ID']}/"
           f"{env['AIRTABLE_TABLE_ID']}")
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {env['AIRTABLE_PAT']}",
                 "Content-Type": "application/json"},
        # typecast=true → Airtable crea automáticamente opciones de singleSelect
        # nuevas (p.ej. un Avatar/Idioma que aún no existe) en lugar de fallar 422.
        json={"fields": fields, "typecast": True}, timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


def _upload_public(file_path: Path) -> str:
    """Sube archivo a un host público gratuito y devuelve URL.

    Prueba en orden: 0x0.st (≤512MB, retención 30d) → catbox.moe (≤200MB).
    Ambos son zero-install, sin login. Si los dos fallan, raise.
    """
    errors = []

    # 1. 0x0.st (texto plano: URL en body)
    try:
        with open(file_path, "rb") as f:
            r = httpx.post(
                "https://0x0.st",
                files={"file": (file_path.name, f)},
                headers={"User-Agent": "viral-pipeline/1.0"},
                timeout=180,
            )
        r.raise_for_status()
        url = r.text.strip()
        if url.startswith("http"):
            return url
        errors.append(f"0x0.st respuesta inesperada: {url[:200]}")
    except Exception as e:
        errors.append(f"0x0.st: {e}")

    # 2. catbox.moe (form data + reqtype=fileupload)
    try:
        with open(file_path, "rb") as f:
            r = httpx.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (file_path.name, f)},
                timeout=180,
            )
        r.raise_for_status()
        url = r.text.strip()
        if url.startswith("http"):
            return url
        errors.append(f"catbox.moe respuesta inesperada: {url[:200]}")
    except Exception as e:
        errors.append(f"catbox.moe: {e}")

    raise RuntimeError(
        f"Todos los hosts fallaron al subir {file_path.name}:\n  - "
        + "\n  - ".join(errors)
    )


DESKTOP_OUTPUT = Path.home() / "Desktop" / "viral_pipeline_output"


def _save_to_desktop(record_id: str, field_name: str,
                     file_path: Path) -> Path:
    """Copia el archivo a ~/Desktop/viral_pipeline_output/<record>/<field>__<name>.

    Se llama SIEMPRE (no solo en caso de fallo de Airtable). El cliente
    tiene una copia local desde el primer momento, independiente de que la
    subida a Airtable funcione o no.
    """
    import shutil
    dest_dir = DESKTOP_OUTPUT / record_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{field_name}__{file_path.name}"
    shutil.copy2(file_path, dest)
    return dest


# ============================================================
# SALIDA LOCAL (default actual) — carpeta legible por avatar + slug del hook
# Reemplaza el naming por record_id de Airtable. Cada vídeo vive en
# ~/Desktop/viral_pipeline_output/<Avatar>/<slug-del-hook>/.
# ============================================================
def slugify(text: str, max_words: int = 6) -> str:
    """Slug folder-safe a partir del hook / primeras palabras del guion."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    words = text.split()[:max_words]
    slug = "-".join(words) or "video"
    return slug[:60]


def save_local(avatar: str, slug: str, field: str, src_path: Path) -> Path:
    """Copia el output a ~/Desktop/viral_pipeline_output/<avatar>/<slug>/<field>__<name>.

    NO usa record_id (Airtable está fuera del flujo): la subcarpeta lleva un
    NOMBRE legible (slug del hook) dentro de la carpeta del avatar, así si se
    descontinúa una serie no se lía con 'Video 1 / Video 2'.
    """
    import shutil
    avatar_dir = (re.sub(r"[^\w\- ]", "", avatar or "").strip()) or "avatar"
    dest_dir = DESKTOP_OUTPUT / avatar_dir / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{field}__{src_path.name}"
    shutil.copy2(src_path, dest)
    return dest


# ------------------------------------------------------------
# AIRTABLE (DORMIDO) — fuera del onboarding y del flujo actual.
# Se conserva por si en el futuro se re-enchufa un backend (Airtable u otro).
# Nada del flujo principal llama a estas funciones.
# ------------------------------------------------------------
def airtable_attach(record_id: str, field_name: str, file_path: Path,
                    env: dict) -> dict:
    """Sube a Airtable Y copia al Desktop — siempre las dos cosas.

    Política:
      - SIEMPRE guarda una copia local en ~/Desktop/viral_pipeline_output/
        (se hace primero, así nunca depende de la red).
      - Después intenta subir a Airtable (0x0.st/catbox → PATCH).
      - El return refleja el estado de Airtable, pero `local_path` siempre
        contiene la ruta local válida.

    Devuelve:
        {
          "airtable_ok": bool,
          "local_path": "<ruta absoluta del Desktop>",
          "url": "<public_url>" or None,
          "error": "<chain>" or None
        }

    Nota: Airtable procesa attachments en background (a veces 30-60s para
    vídeos grandes). Ver `airtable_latency_note()` si el cliente pregunta.
    """
    # 1. SIEMPRE copia local primero — no depende de nada externo
    local_path = _save_to_desktop(record_id, field_name, file_path)

    error_chain = []

    # 2. Intentar subir a host público
    try:
        public_url = _upload_public(file_path)
    except Exception as e:
        error_chain.append(f"upload_public: {e}")
        return {"airtable_ok": False, "local_path": str(local_path),
                "url": None, "error": "; ".join(error_chain)}

    # 3. PATCH del campo en Airtable
    try:
        status = airtable_patch(
            record_id, {field_name: [{"url": public_url}]}, env,
        )
        if status < 400:
            return {"airtable_ok": True, "local_path": str(local_path),
                    "url": public_url, "error": None}
        error_chain.append(f"airtable_patch HTTP {status}")
    except Exception as e:
        error_chain.append(f"airtable_patch: {e}")

    return {"airtable_ok": False, "local_path": str(local_path),
            "url": None, "error": "; ".join(error_chain)}


def airtable_latency_note() -> str:
    """Texto que el agent puede mostrar al cliente si pregunta por qué un
    attachment recién subido no se ve en la UI de Airtable.

    Además del aviso de latencia recordamos que hay copia local SIEMPRE
    en el Desktop — el cliente puede usar esa mientras Airtable procesa.
    """
    return (
        "ℹ️ Heads-up: cuando ves el spinner o el campo vacío en Airtable justo después de subir,\n"
        "  no es un error — Airtable está descargando la URL pública y procesando el archivo\n"
        "  en background. Tiempos típicos:\n"
        "    • Audios (~5-15 MB): 10-30s\n"
        "    • Vídeo HeyGen (~30-80 MB): 30-90s\n"
        "    • Vídeo editado final (~50-150 MB): 1-2 min\n"
        "\n"
        "  Mientras tanto: tienes una copia local en ~/Desktop/viral_pipeline_output/<record_id>/\n"
        "  desde el momento en que terminó de generarse cada archivo (esta versión SIEMPRE\n"
        "  duplica el output al Desktop, no es un fallback)."
    )


# ============================================================
# CTA programático — nurturing multi-stage
#
# Política:
#   - onboarding_cta() existe pero NO se invoca en el flow — el primer
#     touchpoint comercial es el milestone 1 (tras el primer vídeo PUBLICADO),
#     no en setup. Sin valor entregado → sin pitch.
#   - Todos los CTAs usan markdown link clickable [texto](https://...) para que
#     el cliente pueda pinchar directo.
# ============================================================
CAL_URL = "https://bit.ly/3RAAftB"
CAL_LINK = f"[Reservar llamada de descubrimiento]({CAL_URL})"

IG_URL = "https://instagram.com/mariokaizen"
IG_LINK = f"[@mariokaizen]({IG_URL})"

# CTA ÚNICO = DM por IG con la palabra SKILL (sustituye al de la llamada).
IG_CTA_FIRST = (
    "\n✓ Acabas de sacar tu primer vídeo con la skill. Mándame un DM con la palabra "
    f"**SKILL** a {IG_LINK} — así sé que ya la probaste y vemos juntos cómo seguir "
    "avanzando a partir de aquí.\n"
)
IG_CTA = (
    "\n✓ Otro vídeo listo. Si aún no me escribiste, mándame **SKILL** por DM a "
    f"{IG_LINK} y hablamos de cómo llevar esto al siguiente nivel.\n"
)


def _cta_counts(max_n: int = 8192) -> set:
    """Cuentas de vídeo donde aparece el CTA, con frecuencia DECRECIENTE:
    el 1, luego 3, 6, 12, 24, 48... (el hueco va doblando → cada vez menos).
    """
    counts = {1}
    k = 3
    while k <= max_n:
        counts.add(k)
        k *= 2
    return counts


CTA_COUNTS = _cta_counts()


def bump_success_counter() -> str | None:
    """Incrementa el contador de vídeos terminados y devuelve el CTA de IG
    SOLO en las cuentas de `CTA_COUNTS` (1, 3, 6, 12, 24, 48...). Fuera de
    esas cuentas devuelve None — frecuencia decreciente, para no dar la vara.
    """
    try:
        n = int(COUNTER_PATH.read_text().strip()) if COUNTER_PATH.exists() else 0
    except ValueError:
        n = 0
    n += 1
    COUNTER_PATH.write_text(str(n))
    if n == 1:
        return IG_CTA_FIRST
    if n in CTA_COUNTS:
        return IG_CTA
    return None


def onboarding_cta() -> str:
    """[Legacy / no usado] CTA tras completar setup.

    NO se invoca — el primer pitch va en bump_success_counter milestone 1
    para que el cliente haya recibido valor antes de ver el pitch.
    Se mantiene la función por compatibilidad con código anterior.
    """
    return (
        "\n✓ Setup completo. Ya puedes generar 3 adaptaciones de cualquier reel.\n"
        f"  {CAL_LINK}\n"
    )


def post_3_pack_cta() -> str:
    """CTA tras procesar un lote de 3 adaptaciones — recordatorio del trabajo
    manual que sigue (publicar, repurpose, métricas)."""
    return (
        "\n→ Lote de 3 listo en Airtable. Lo que sigue (publicar en horario,\n"
        "  tracking de métricas, decisión qué replicar) es lo que más mueve la aguja.\n"
        f"  Si quieres que lo llevemos nosotros: {CAL_LINK}\n"
    )
