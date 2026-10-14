@echo off
REM ============================================================
REM  Paso 1 - Transcripcion  -  whisper.cpp large-v3 + DTW (100%% local)
REM  Uso:
REM    transcribir.bat <proyecto>                 -> TODO lo de proyectos\<proyecto>\input\
REM    transcribir.bat <proyecto> "v.mp4"         -> un archivo de su input\ (o una ruta)
REM    transcribir.bat <proyecto> "" en           -> forzar idioma (def: el del proyecto)
REM  Resultado en proyectos\<proyecto>\transcripciones\<nombre>\ (.txt, .srt, .json).
REM ============================================================
setlocal
set "SCRIPTDIR=%~dp0"
set "PY=%SCRIPTDIR%.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] No se encuentra el entorno virtual en "%PY%".
  exit /b 1
)

set "PROYECTO=%~1"
set "ARCHIVO=%~2"
set "IDIOMA=%~3"

if "%PROYECTO%"=="" (
  echo [ERROR] Indica el proyecto: transcribir.bat ^<proyecto^> [archivo] [idioma]
  exit /b 1
)

set "ARGS= --proyecto %PROYECTO%"
if not "%ARCHIVO%"=="" set "ARGS=%ARGS% "%ARCHIVO%""
if not "%IDIOMA%"==""  set "ARGS=%ARGS% --idioma %IDIOMA%"

"%PY%" "%SCRIPTDIR%transcribir.py"%ARGS%

echo.
pause
endlocal
