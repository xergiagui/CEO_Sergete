"""
Render de la historia: FONDO (vídeo del proyecto o color liso) + FRASE encima → MP4 9:16.

Estrategia:
  1. Con Pillow se dibuja una CAPA de texto 1080x1920 transparente: un scrim
     oscuro a pantalla completa (legibilidad) + la frase centrada, envuelta,
     con sombra. Se guarda como PNG temporal.
  2. Con ffmpeg (el bundled de imageio-ffmpeg, sin depender del sistema) se
     escala/recorta el fondo a 1080x1920 "cover", se superpone el PNG y se
     exporta un MP4 H.264 de STORY_DURATION segundos. Sin vídeo (política de
     b-roll `ninguno`), el fondo es un color liso de marca (fuente lavfi `color`).

Silencioso por defecto (una historia de texto no necesita el audio del b-roll).
"""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

import config
from lib.texto import capitalizar_frase


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    """Envuelve `text` en líneas que caben en `max_w` px con `font`."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        probe = (cur + " " + w).strip()
        if draw.textlength(probe, font=font) <= max_w or not cur:
            cur = probe
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# Rango de tamaños de fuente para el auto-ajuste. El máximo es el ideal para
# one-liners; el mínimo garantiza que un bloque largo de transcripción (1500+
# caracteres) SIEMPRE quepa y siga siendo legible en 9:16. Nunca se descarta una
# frase por longitud: se reduce la fuente hasta que entra en el área segura.
_FONT_MAX = 96
_FONT_MIN = 24
_LINE_SPACING = 1.28   # factor alto-de-línea → alto-de-bloque (debe casar con el gap del pintado)


def _fit_font(draw, text: str, max_w: int, max_h: int,
              font_path: Path) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Elige el MAYOR tamaño de fuente con el que el texto (envuelto en líneas)
    cabe en la caja (max_w × max_h). Baja el tamaño dinámicamente para frases
    largas; si ni el mínimo cupiera, devuelve el mínimo (mejor legible que nada).
    """
    for size in range(_FONT_MAX, _FONT_MIN - 1, -2):
        font = ImageFont.truetype(str(font_path), size)
        lines = _wrap(draw, text, font, max_w)
        line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        total_h = int(len(lines) * line_h * _LINE_SPACING)
        if total_h <= max_h:
            return font, lines
    font = ImageFont.truetype(str(font_path), _FONT_MIN)
    return font, _wrap(draw, text, font, max_w)


def _build_text_png(phrase: str, out_png: Path,
                    bottom_reserved_frac: float = 0.0,
                    oscurecer: Optional[float] = None) -> None:
    """Capa 1080x1920 RGBA: scrim + frase centrada con sombra.

    `bottom_reserved_frac` (0..1): fracción de la altura reservada ABAJO (p. ej.
    para el botón de Instagram en las historias especiales). Con 0.0 el texto se
    centra en TODA la pantalla (comportamiento original). Con >0.0 el bloque de
    texto se compone y se centra dentro de la ZONA SUPERIOR
    [margen_sup .. H*(1-bottom_reserved_frac)]; el scrim sigue a pantalla completa.
    """
    W, H = config.STORY_W, config.STORY_H
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Scrim oscuro a pantalla completa (legibilidad sobre cualquier fondo).
    osc = config.FONDO_OSCURECER if oscurecer is None else oscurecer
    scrim_alpha = int(max(0.0, min(1.0, osc)) * 255)
    if scrim_alpha:
        draw.rectangle([0, 0, W, H], fill=(0, 0, 0, scrim_alpha))

    # Regla de Sergio: minúsculas salvo inicio de oración. Se aplica AQUÍ, justo
    # donde se pinta el texto, para que valga en todo el flujo (BBDD o --phrase).
    texto = capitalizar_frase(phrase.strip())

    font_path = config.FONTS_DIR / "Montserrat-Bold.ttf"
    margin_x = 90
    max_w = W - 2 * margin_x

    # Zona segura vertical donde se compone y se centra el bloque de texto.
    frac = max(0.0, min(0.6, float(bottom_reserved_frac)))
    if frac > 0.0:
        # Deja libre la franja inferior (botón de IG). El texto vive en
        # [zona_top .. zona_bottom] y se centra DENTRO de esa zona.
        margin_top = int(H * 0.10)
        zona_bottom = int(H * (1.0 - frac))
        zona_top = margin_top
        max_h = max(1, zona_bottom - zona_top)
    else:
        # Comportamiento original: área amplia, centrado en pantalla completa.
        max_h = int(H * 0.78)
        zona_top = 0
        zona_bottom = H

    font, lines = _fit_font(draw, texto, max_w, max_h, font_path)

    line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
    gap = int(line_h * (_LINE_SPACING - 1.0))
    block_h = len(lines) * line_h + (len(lines) - 1) * gap
    y = zona_top + (zona_bottom - zona_top - block_h) // 2

    for line in lines:
        tw = draw.textlength(line, font=font)
        x = (W - tw) // 2
        # Sombra + texto.
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 210))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h + gap

    img.save(out_png)


def render_historia(
    fondo: Optional[Path], phrase: str, out_mp4: Path,
    duration: Optional[float] = None,
    bottom_reserved_frac: float = 0.0,
    color: Optional[str] = None,
) -> Path:
    """Compone el MP4 9:16 (fondo cover + frase). Devuelve la ruta de salida.

    `fondo` = vídeo; si es None, fondo liso de `color` (#rrggbb; def. el de
    config) sin scrim. `bottom_reserved_frac` (0..1): reserva una franja inferior
    sin texto (botón de IG). 0.0 = texto centrado en pantalla completa.
    """
    duration = duration or config.STORY_DURATION
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "texto.png"
        _build_text_png(phrase, png, bottom_reserved_frac=bottom_reserved_frac,
                        oscurecer=0.0 if fondo is None else None)

        W, H, fps = config.STORY_W, config.STORY_H, config.STORY_FPS
        if fondo is None:
            hexa = (color or config.FONDO_LISO_DEFECTO).lstrip("#")
            entrada = ["-f", "lavfi", "-i", f"color=c=0x{hexa}:s={W}x{H}:r={fps}"]
            vf_bg = "setsar=1"
        else:
            entrada = ["-stream_loop", "-1", "-i", str(fondo)]   # loop si es corto
            vf_bg = (
                f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},fps={fps},setsar=1"
            )
        cmd = [
            _ffmpeg_exe(), "-y",
            *entrada,                                 # fondo
            "-loop", "1", "-i", str(png),             # capa de texto (imagen fija)
            "-filter_complex",
            f"[0:v]{vf_bg}[bg];[bg][1:v]overlay=0:0:format=auto[v]",
            "-map", "[v]",
            "-t", f"{duration}",
            "-r", str(fps),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
            "-movflags", "+faststart", "-an",
            str(out_mp4),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not out_mp4.exists():
            raise RuntimeError(f"ffmpeg falló:\n{(r.stderr or '')[-800:]}")
    return out_mp4
