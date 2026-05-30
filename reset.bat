@echo off
title NEXUS - Reset Training Data
cd /d "%~dp0"
echo.
echo ============================================
echo   NEXUS — Training Data Reset
echo ============================================
echo.
echo   WARNING: This will delete all custom training
echo   data from the lora-weights/ folder.
echo   NEXUS will revert to the base model.
echo.
python src/model_manager.py
echo.
pause
