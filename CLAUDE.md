# TheDescarga — Departamento de descarga

Baja vídeo o audio de YouTube, Instagram, TikTok y otras webs con `yt-dlp`
local. Lo dirige CEO_Sergete con el subagente `descarga`. Uso detallado en
[`README.md`](README.md).

## Reglas
- **Autónomo, sin instalar nada:** usa siempre `tools\yt-dlp.exe` (con
  `tools\ffmpeg.exe`/`ffprobe.exe` al lado). Nada de yt-dlp, ffmpeg ni Python
  globales.
- Salida siempre en `descargas\`, con el título como nombre:
  `-o "descargas/%(title)s.%(ext)s"`.
- Por defecto, **solo el vídeo de la URL** (`--no-playlist`). Si la URL es una
  lista, pregunta antes de bajarla entera.
- Vídeo: `-f "bv*+ba/b" --merge-output-format mp4`. Audio: `-x --audio-format mp3 --audio-quality 0`.
- Contenido privado o que pide login: `--cookies-from-browser chrome`.
- El aviso de «JavaScript runtime» es normal. Si falla una web que antes iba,
  actualiza primero: `tools\yt-dlp.exe -U`.

## Handoff con TheEditor
Lo que se baja aquí se trata después en TheEditor. Devuelve la **ruta exacta** del
MP4 en `descargas\`: el subagente `editor` lo copia a su buzón `TheEditor\input\`.
No lo copies tú.
