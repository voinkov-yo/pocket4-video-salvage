@echo off
setlocal DisableDelayedExpansion
python -m pip install --disable-pip-version-check --no-deps --target "%~dp0vendor" imageio-ffmpeg==0.8.1
if errorlevel 1 (
  echo Installation failed. Check that Python and internet are available.
) else (
  echo Installation finished. Drag a recovered MP4 onto Восстановить_MP4.cmd.
)
pause
