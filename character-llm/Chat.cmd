@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Ollama.ps1"
if errorlevel 1 goto end
python character_chat.py chat
:end
pause
