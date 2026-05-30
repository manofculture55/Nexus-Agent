@echo off
title NEXUS - Training Pipeline
cd /d "%~dp0"
call venv\Scripts\activate
echo Starting NEXUS training pipeline...
echo Make sure your dataset .txt files are in the datasets/ folder
echo For faster training: python src/trainer.py --quick
echo.
python src/trainer.py %*
echo.
echo Training session complete. Press any key to close.
pause
