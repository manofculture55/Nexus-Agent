@echo off
title NEXUS - Quick Open Overlay
cd /d "%~dp0"
echo Starting NEXUS Quick Open overlay...
echo Press Ctrl+Alt+N to show/hide the window.
echo.
REM Use the venv's pythonw directly so the overlay runs without a console window.
REM The CMD window will close after launch — the overlay runs independently.
start "" venv\Scripts\pythonw.exe src/quick_open.py
