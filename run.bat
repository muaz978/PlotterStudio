@echo off
REM Plotter Studio launcher for Windows.
REM First run: sets up a private virtualenv, installs deps, fetches potrace.
REM Later runs: just launches. Double-click this file.
setlocal
cd /d "%~dp0"

echo === Plotter Studio setup ===

REM 1) potrace (high-quality tracer). If not on PATH and not already local, download it.
where potrace >nul 2>nul
if errorlevel 1 (
  if not exist bin\potrace.exe (
    echo   downloading potrace...
    powershell -NoProfile -Command "try { Invoke-WebRequest 'https://potrace.sourceforge.net/download/1.16/potrace-1.16.win64.zip' -OutFile 'potrace.zip'; Expand-Archive 'potrace.zip' -DestinationPath 'potrace_tmp' -Force } catch { Write-Host '  could not download potrace automatically' }"
    if not exist bin mkdir bin
    if exist potrace_tmp\potrace-1.16.win64\potrace.exe copy potrace_tmp\potrace-1.16.win64\potrace.exe bin\ >nul
    if exist potrace.zip del potrace.zip
    if exist potrace_tmp rmdir /s /q potrace_tmp
  )
)

REM 2) private virtualenv + Python deps
if not exist .venv (
  echo   creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\python -m pip install --quiet --upgrade pip
call .venv\Scripts\python -m pip install --quiet -r requirements.txt

REM 3) launch
echo === starting Plotter Studio ===
call .venv\Scripts\python plotter_studio.py
if errorlevel 1 pause
