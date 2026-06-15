@echo off
cd /d "%~dp0"
title Video Downloader
echo Starting Video Downloader...
echo.
.\venv_new\Scripts\python.exe app.py
pause
