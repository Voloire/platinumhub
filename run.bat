@echo off
title Platinum Hub - by Voloirex
cd /d "%~dp0"

REM --- find a working Python 3 -------------------------------------------
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app.py
    goto end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python app.py
    goto end
)

where python3 >nul 2>nul
if %errorlevel%==0 (
    python3 app.py
    goto end
)

echo.
echo  ============================================================
echo   Python 3 was not found on this PC.
echo.
echo   Install it once (it is free, ~30 seconds):
echo     - open the Microsoft Store and install "Python 3.12"
echo     - or download it from https://www.python.org/downloads/
echo       (tick "Add python.exe to PATH" in the installer)
echo.
echo   Then double-click run.bat again.
echo  ============================================================
echo.

:end
echo.
pause
