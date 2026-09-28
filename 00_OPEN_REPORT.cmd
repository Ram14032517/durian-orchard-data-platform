@echo off
cd /d "%~dp0"
where code >nul 2>nul
if errorlevel 1 (
  echo Open 00_OPEN_ME.ipynb in Visual Studio Code.
  start "" "%~dp000_OPEN_ME.ipynb"
  exit /b
)
call code --reuse-window "%~dp000_OPEN_ME.ipynb"
