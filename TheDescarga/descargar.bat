@echo off
REM ============================================================
REM  TheDescarga  -  yt-dlp autonomo (sin instalar nada)
REM  Uso:  descargar.bat "URL" [modo] [proyecto]
REM        modo:     best (por defecto, MP4) | audio (MP3) | 1080p | 720p | 480p | 360p
REM        proyecto: id del proyecto (p. ej. mongemalo) -> descargas\<proyecto>\
REM                  sin proyecto -> descargas\_general\
REM  Ej.:  descargar.bat "URL" best mongemalo     descargar.bat "URL" audio
REM  Los binarios (yt-dlp + ffmpeg) viven en la carpeta tools\.
REM ============================================================
setlocal enabledelayedexpansion
set "SCRIPTDIR=%~dp0"
set "YTDLP=%SCRIPTDIR%tools\yt-dlp.exe"
set "PROY=%~3"
if "%PROY%"=="" set "PROY=_general"
set "OUT=%SCRIPTDIR%descargas\%PROY%"
if not exist "%OUT%" mkdir "%OUT%"

if not exist "%YTDLP%" (
  echo [ERROR] No se encuentra yt-dlp en "%YTDLP%".
  exit /b 1
)

if "%~1"=="" (
  echo Uso: descargar.bat "URL" [best^|audio^|1080p^|720p^|480p^|360p] [proyecto]
  exit /b 1
)

set "URL=%~1"
set "MODE=%~2"

if /I "%MODE%"=="audio" goto audio
if "%MODE%"=="" goto best
if /I "%MODE%"=="best" goto best
goto quality

:audio
"%YTDLP%" -x --audio-format mp3 --audio-quality 0 -o "%OUT%\%%(title)s.%%(ext)s" --no-playlist --print after_move:filepath "%URL%"
set "RC=!ERRORLEVEL!"
goto done

:best
"%YTDLP%" -f "bv*+ba/b" --merge-output-format mp4 -o "%OUT%\%%(title)s.%%(ext)s" --no-playlist --print after_move:filepath "%URL%"
set "RC=!ERRORLEVEL!"
goto done

:quality
set "H=%MODE:p=%"
"%YTDLP%" -f "bv*[height<=!H!]+ba/b[height<=!H!]" --merge-output-format mp4 -o "%OUT%\%%(title)s.%%(ext)s" --no-playlist --print after_move:filepath "%URL%"
set "RC=!ERRORLEVEL!"
goto done

REM --print after_move:filepath: en silencio y solo imprime la ruta final del archivo.
:done
if not "%RC%"=="0" (
  echo [ERROR] yt-dlp termino con codigo %RC%.
  endlocal & exit /b %RC%
)
endlocal & exit /b 0
