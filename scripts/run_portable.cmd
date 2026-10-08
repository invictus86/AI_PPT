@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONHOME="
set "PYTHONPATH="
set "PPT_SKILL_WORKSPACE_ROOT="
set "PPT_SKILL_INPUT_ROOT="
set "PPT_SKILL_OUTPUT_ROOT="
set "PPTCTL_NO_BUNDLED_PYTHON=1"
set "PPT_PYTHON=%~dp0..\_local\python\python.exe"
if not exist "%PPT_PYTHON%" (
  echo Portable runtime is missing. Please use the private portable package first.
  if not "%PPT_SYNC_NO_PAUSE%"=="1" pause
  exit /b 1
)
"%PPT_PYTHON%" -X utf8 -B "%~dp0computer_sync.py" %*
set "PPT_RESULT=%errorlevel%"
if not "%PPT_SYNC_NO_PAUSE%"=="1" pause
exit /b %PPT_RESULT%
