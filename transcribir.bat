@echo off
REM ============================================================
REM  Paso 1 - Transcripcion  -  whisper.cpp large-v3 + DTW (100%% local)
REM  Uso:
REM    transcribir.bat                 -> transcribe TODO lo de input\
REM    transcribir.bat "input\v.mp4"   -> un archivo concreto
REM    transcribir.bat "" en           -> forzar idioma (def: es)
REM  Resultado en transcripciones\<nombre>\ (.txt, .srt, .json).
REM ============================================================
setlocal
set "SCRIPTDIR=%~dp0"
set "PY=%SCRIPTDIR%.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] No se encuentra el entorno virtual en "%PY%".
  exit /b 1
)

set "ARCHIVO=%~1"
set "IDIOMA=%~2"

set "ARGS="
if not "%ARCHIVO%"=="" set "ARGS=%ARGS% "%ARCHIVO%""
if not "%IDIOMA%"==""  set "ARGS=%ARGS% --idioma %IDIOMA%"

"%PY%" "%SCRIPTDIR%transcribir.py"%ARGS%

echo.
pause
endlocal
