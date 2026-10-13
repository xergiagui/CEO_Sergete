# TheDescarga — Departamento de descarga

Baja vídeo o audio de YouTube, Instagram, TikTok y otras webs con `yt-dlp`
local. Lo dirige CEO_Sergete con el subagente `descarga`. Uso detallado en
[`README.md`](README.md).

## Reglas
- **Autónomo, sin instalar nada:** usa siempre `tools\yt-dlp.exe` (con
  `tools\ffmpeg.exe`/`ffprobe.exe` al lado). Nada de yt-dlp, ffmpeg ni Python
  globales.
- **Por proyecto:** salida en `descargas\<proyecto>\` (p. ej. `descargas\mongemalo\`),
  con el título como nombre: `-o "descargas/<proyecto>/%(title)s.%(ext)s"`. Lo que
  no sea de ningún proyecto va a `descargas\_general\`. Si el CEO no dice el
  proyecto y no es evidente, pregúntaselo; nunca mezcles proyectos.
- Por defecto, **solo el vídeo de la URL** (`--no-playlist`). Si la URL es una
  lista, pregunta antes de bajarla entera.
- Vídeo: `-f "bv*+ba/b" --merge-output-format mp4`. Audio: `-x --audio-format mp3 --audio-quality 0`.
- Contenido privado o que pide login: `--cookies-from-browser chrome`.
- El aviso de «JavaScript runtime» es normal. Si falla una web que antes iba,
  actualiza primero: `tools\yt-dlp.exe -U`.
- **Lo normal:** `descargar.bat "URL" [modo] <proyecto>`. Va en silencio, imprime **solo la
  ruta final** del archivo y sale con código ≠ 0 si falla (no hace falta listar la carpeta).

## Handoff con TheEditor
Lo que se baja aquí se trata después en TheEditor. Devuelve la **ruta exacta** del
archivo en `descargas\<proyecto>\`: el subagente `editor` lo **mueve** (no copia: son
vídeos de varios GB) a su buzón `TheEditor\proyectos\<proyecto>\input\`. No lo muevas tú.
