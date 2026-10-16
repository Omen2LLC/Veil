@echo off
setlocal
cd /d "%~dp0"
set "VEIL_ARGUMENT="
if "%~1"=="--check" set "VEIL_ARGUMENT=--check"
py -3 "%~dp0veil_start.py" --check-runtime >nul 2>&1
if not errorlevel 1 goto use_py
python "%~dp0veil_start.py" --check-runtime >nul 2>&1
if not errorlevel 1 goto use_python
goto missing
:use_py
py -3 "%~dp0veil_start.py" %VEIL_ARGUMENT%
exit /b %errorlevel%
:use_python
python "%~dp0veil_start.py" %VEIL_ARGUMENT%
exit /b %errorlevel%
:missing
>launcher-error.txt echo Veil needs Windows and 64-bit Python 3.11 or newer with Tcl/Tk.
exit /b 1
