@echo off
setlocal
cd /d "%~dp0"
set "OMEN_ARGUMENT="
if "%~1"=="--check" set "OMEN_ARGUMENT=--check"
py -3 "%~dp0start_omen_studio.py" --check-runtime >nul 2>&1
if not errorlevel 1 goto use_py
python "%~dp0start_omen_studio.py" --check-runtime >nul 2>&1
if not errorlevel 1 goto use_python
set "OMEN_LOCAL_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%OMEN_LOCAL_PYTHON%" goto missing
"%OMEN_LOCAL_PYTHON%" "%~dp0start_omen_studio.py" --check-runtime >nul 2>&1
if not errorlevel 1 goto use_local
goto missing
:use_py
py -3 "%~dp0start_omen_studio.py" %OMEN_ARGUMENT%
exit /b %errorlevel%
:use_python
python "%~dp0start_omen_studio.py" %OMEN_ARGUMENT%
exit /b %errorlevel%
:use_local
"%OMEN_LOCAL_PYTHON%" "%~dp0start_omen_studio.py" %OMEN_ARGUMENT%
exit /b %errorlevel%
:missing
>launcher-error.txt echo Veil needs Windows and 64-bit Python 3.11 or newer with Tcl/Tk.
exit /b 1
