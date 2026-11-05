@echo off
setlocal DisableDelayedExpansion
python "%~dp0recover_video.py" "%~1"
pause
