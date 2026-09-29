@echo off
rem moon-tracker launcher: checks git + Python, bootstraps uv, syncs, runs.
rem Double-click to start. Update with: git pull --ff-only
setlocal EnableDelayedExpansion
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
  echo [moon-tracker] git not found. Install it first:
  echo   https://git-scm.com/download/win
  pause
  exit /b 1
)

for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set BRANCH=%%b
if defined BRANCH (
  if not "%BRANCH%"=="main" echo [moon-tracker] WARNING: not on branch 'main' ^(on '%BRANCH%'^). Continuing...
)

set PY=
for %%P in ("py -3.12" "py -3.11" "py -3.10" "py -3" python) do (
  if not defined PY (
    %%~P -c "import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
    if not errorlevel 1 set PY=%%~P
  )
)

where uv >nul 2>nul
if errorlevel 1 (
  echo [moon-tracker] Installing uv package manager...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" 2>nul
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
where uv >nul 2>nul
if errorlevel 1 (
  echo [moon-tracker] uv not found after install. Open a NEW terminal and re-run run.bat.
  echo   Or install manually: https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)

if not defined PY (
  echo [moon-tracker] No Python 3.10+ found. Installing Python 3.12 via uv...
  uv python install 3.12
  if errorlevel 1 (
    echo [moon-tracker] Python install failed. Install manually:
    echo   https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
  set PY=python
)

if not exist ".venv" echo [moon-tracker] First run: downloading dependencies, ~100MB for Flet, please wait...
if not exist ".venv" echo [moon-tracker] Windows may show a firewall prompt for the tracker window - this is expected.

rem NOTE: uv chooses the .venv interpreter itself; PY above only gates the
rem Python-install fallback. uv.lock is interpreter-agnostic, so the env matches.
uv sync --frozen
if errorlevel 1 (
  echo [moon-tracker] Dependency sync failed. Check your connection and re-run.
  pause
  exit /b 1
)

uv run --frozen python -m moon_tracker %*
