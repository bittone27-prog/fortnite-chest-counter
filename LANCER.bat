@echo off
title Fortnite Chest Counter
python --version >nul 2>&1
if errorlevel 1 (
  echo Python n'est pas installe. Installe-le depuis https://www.python.org/downloads/
  echo IMPORTANT : coche la case "Add Python to PATH" pendant l'installation.
  pause
  exit /b
)
python -m pip install -r requirements.txt
python chest_counter.py
pause
