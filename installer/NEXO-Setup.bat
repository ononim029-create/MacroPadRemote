@echo off
setlocal EnableExtensions
set "SETUP_NAME=NEXO-Setup.exe"
set "LOCAL_SETUP=%~dp0%SETUP_NAME%"
set "TEMP_SETUP=%TEMP%\%SETUP_NAME%"
set "SETUP_URL=https://github.com/ononim029-create/MacroPadRemote/releases/download/preview/%SETUP_NAME%"

if exist "%LOCAL_SETUP%" (
    start "" "%LOCAL_SETUP%"
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest -UseBasicParsing '%SETUP_URL%' -OutFile '%TEMP_SETUP%'"
if errorlevel 1 (
    echo NEXO Setup could not be downloaded.
    echo Open the NEXO Preview release and download NEXO-Setup.exe manually.
    pause
    exit /b 1
)

start "" "%TEMP_SETUP%"
exit /b 0
