@echo off
title NEXUS - Offline AI Agent
cd /d "%~dp0"
call venv\Scripts\activate
python src/agent.py
pause
