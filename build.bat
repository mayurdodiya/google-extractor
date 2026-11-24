@echo off
REM Builds dist\GoogleExtractor.exe (single file, no Python needed on target PC)
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt
python -m pytest -q || goto :error
pyinstaller --noconfirm --onefile --windowed --name GoogleExtractor --collect-all playwright --collect-all ttkbootstrap app.py || goto :error
echo.
echo Build complete: dist\GoogleExtractor.exe
goto :eof
:error
echo Build FAILED.
exit /b 1
