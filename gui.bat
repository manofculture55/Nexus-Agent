@echo off
title NEXUS - Offline AI Agent (GUI)
cd /d "%~dp0"
call venv\Scripts\activate
python src/gui.py
pause
