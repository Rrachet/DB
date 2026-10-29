@echo off
cd /d "%~dp0"
title DB
call .venv\Scripts\activate.bat
python -m db %*
