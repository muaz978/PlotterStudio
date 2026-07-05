@echo off
REM Build a standalone PlotterStudio.exe (bundles Python + potrace).
REM Result: dist\PlotterStudio.exe
setlocal
cd /d "%~dp0"

REM ensure potrace is available locally (run run.bat once, or place bin\potrace.exe)
if not exist bin\potrace.exe (
  echo Fetching potrace...
  powershell -NoProfile -Command "Invoke-WebRequest 'https://potrace.sourceforge.net/download/1.16/potrace-1.16.win64.zip' -OutFile 'potrace.zip'; Expand-Archive 'potrace.zip' -DestinationPath 'potrace_tmp' -Force"
  if not exist bin mkdir bin
  copy potrace_tmp\potrace-1.16.win64\potrace.exe bin\ >nul
  del potrace.zip
  rmdir /s /q potrace_tmp
)

python -m venv .buildenv
call .buildenv\Scripts\python -m pip install --quiet --upgrade pip pyinstaller
call .buildenv\Scripts\python -m pip install --quiet -r requirements.txt
call .buildenv\Scripts\pyinstaller --noconfirm --windowed --name PlotterStudio ^
  --add-binary "bin\potrace.exe;bin" ^
  plotter_studio.py

echo Built dist\PlotterStudio.exe
