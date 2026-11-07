@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0backend
set PYTHONIOENCODING=utf-8
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0desktop\main.py"
