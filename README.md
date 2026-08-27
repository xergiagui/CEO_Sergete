# TheDescarga

> Departamento de **descarga de vídeo** del sistema **CEO_Sergete**.
> (Antes «Descargador de Videos».)

Descarga vídeos de **YouTube**, **Instagram** y muchas otras webs con
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp) — 100% gratis, sin API externa y
**sin instalar nada** en el sistema.

## Cómo funciona

Todo es autónomo: los binarios viven en la carpeta [`tools/`](tools/) y no
dependen de que Python, yt-dlp o ffmpeg estén instalados en Windows.

- `tools/yt-dlp.exe` — el descargador.
- `tools/ffmpeg.exe` + `tools/ffprobe.exe` — para fusionar vídeo + audio
  (YouTube entrega los streams por separado, así que hacen falta).

Los vídeos se guardan en la carpeta [`descargas/`](descargas/).

## Uso rápido (doble clic o terminal)

```bat
descargar.bat "https://www.youtube.com/watch?v=VIDEO_ID"
descargar.bat "https://www.instagram.com/reel/CODIGO/"
descargar.bat "URL" audio      :: solo MP3
descargar.bat "URL" 720p       :: calidad concreta
```

## Uso directo con el binario local

```bat
:: Mejor calidad, MP4 (ffmpeg se detecta solo porque está junto a yt-dlp.exe)
tools\yt-dlp.exe -f "bv*+ba/b" --merge-output-format mp4 -o "descargas/%(title)s.%(ext)s" --no-playlist "URL"

:: Solo audio MP3
tools\yt-dlp.exe -x --audio-format mp3 --audio-quality 0 -o "descargas/%(title)s.%(ext)s" --no-playlist "URL"
```

## Pídeselo a Claude Code (recomendado)

Con este proyecto abierto, basta con pegar una URL y decir *"descárgame este
vídeo"*. Claude usa los binarios de `tools/` y deja el archivo en `descargas/`.

## Notas / limitaciones

- **Playlists**: por defecto se descarga **solo el vídeo** de la URL, no la lista
  entera. Para la lista completa, quita `--no-playlist`.
- **Instagram**: reels y posts **públicos** funcionan directamente. Contenido
  privado, stories o cuentas privadas requieren cookies del navegador:
  `tools\yt-dlp.exe --cookies-from-browser chrome "URL"`.
- **Aviso de "JavaScript runtime"**: es normal; la descarga funciona igual. Si a
  algún vídeo le faltaran calidades, instala deno (`winget install DenoLand.Deno`).
- **Actualizar yt-dlp** de vez en cuando: `tools\yt-dlp.exe -U`.
