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
set "PPT_IMAGE_RESOLUTION_PYTHON=%~dp0..\_local\python\python.exe"
if exist "%PPT_IMAGE_RESOLUTION_PYTHON%" (
  "%PPT_IMAGE_RESOLUTION_PYTHON%" -X utf8 -B "%~dp0pptctl.py" image-resolution-menu
) else (
  python -X utf8 -B "%~dp0pptctl.py" image-resolution-menu
)
set "PPT_IMAGE_RESOLUTION_RESULT=%errorlevel%"
if not "%PPT_IMAGE_RESOLUTION_NO_PAUSE%"=="1" pause
exit /b %PPT_IMAGE_RESOLUTION_RESULT%
