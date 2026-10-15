@echo off
rem Entry point. For no console flash, double-click run.vbs directly.
cd /d "%~dp0"

set "MOON_TRACKER_DIAGNOSTIC="
for %%A in (%*) do (
  if /I "%%~A"=="--once" set "MOON_TRACKER_DIAGNOSTIC=1"
  if /I "%%~A"=="--shot" set "MOON_TRACKER_DIAGNOSTIC=1"
  if /I "%%~A"=="--version" set "MOON_TRACKER_DIAGNOSTIC=1"
)

if not defined MOON_TRACKER_DIAGNOSTIC if not defined MOON_TRACKER_FOREGROUND (
  wscript.exe //nologo "%~dp0run.vbs" %*
  exit /b %errorlevel%
)

rem Diagnostic commands intentionally keep their output in this console.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
exit /b %errorlevel%
