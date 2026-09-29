@echo off
cd /d "%~dp0"
echo Installing required packages (first time only)...
python -m pip install -r requirements.txt
echo.
python download_legislation.py
echo.
pause
