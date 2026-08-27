@echo off
REM ============================================================
REM  TheDescarga  -  yt-dlp autonomo (sin instalar nada)
REM  Uso:  descargar.bat "URL"           -> mejor calidad, MP4
REM        descargar.bat "URL" audio     -> solo audio MP3
REM        descargar.bat "URL" 720p      -> calidad concreta MP4
REM  Los binarios (yt-dlp + ffmpeg) viven en la carpeta tools\.
REM ============================================================
setlocal enabledelayedexpansion
set "SCRIPTDIR=%~dp0"
set "YTDLP=%SCRIPTDIR%tools\yt-dlp.exe"
set "OUT=%SCRIPTDIR%descargas"
if not exist "%OUT%" mkdir "%OUT%"

if not exist "%YTDLP%" (
  echo [ERROR] No se encuentra yt-dlp en "%YTDLP%".
  exit /b 1
)

if "%~1"=="" (
  echo Uso: descargar.bat "URL" [audio^|1080p^|720p^|480p^|360p]
  exit /b 1
)

set "URL=%~1"
set "MODE=%~2"

if /I "%MODE%"=="audio" goto audio
if "%MODE%"=="" goto best
goto quality

:audio
"%YTDLP%" -x --audio-format mp3 --audio-quality 0 -o "%OUT%\%%(title)s.%%(ext)s" --no-playlist "%URL%"
goto done

:best
"%YTDLP%" -f "bv*+ba/b" --merge-output-format mp4 -o "%OUT%\%%(title)s.%%(ext)s" --no-playlist "%URL%"
goto done

:quality
set "H=%MODE:p=%"
"%YTDLP%" -f "bv*[height<=!H!]+ba/b[height<=!H!]" --merge-output-format mp4 -o "%OUT%\%%(title)s.%%(ext)s" --no-playlist "%URL%"
goto done

:done
echo.
echo Guardado en: %OUT%
endlocal
