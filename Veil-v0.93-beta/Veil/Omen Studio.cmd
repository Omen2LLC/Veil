@echo off
if "%~1"=="--check" (
  call "%~dp0launch_silent.cmd" --check
  exit /b
)
start "" "%SystemRoot%\System32\wscript.exe" "%~dp0Veil.vbs"
exit /b
