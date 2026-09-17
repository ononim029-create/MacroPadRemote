@echo off
setlocal EnableExtensions
title NEXO Setup

echo.
echo ==============================
echo        NEXO Setup v1.1
echo ==============================
echo.

set "DEFAULT_DIR=%LOCALAPPDATA%\NEXO"
set /p "INSTALL_DIR=Install folder [%DEFAULT_DIR%]: "
if not defined INSTALL_DIR set "INSTALL_DIR=%DEFAULT_DIR%"

echo.
echo Downloading NEXO...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $d=$env:INSTALL_DIR; $u='https://github.com/ononim029-create/MacroPadRemote/releases/download/preview/NEXO-win-x64.zip'; $z=Join-Path $env:TEMP 'NEXO-win-x64.zip'; Invoke-WebRequest -UseBasicParsing $u -OutFile $z; if(Test-Path $d){Remove-Item $d -Recurse -Force}; New-Item -ItemType Directory -Force $d | Out-Null; Expand-Archive $z $d -Force; Remove-Item $z -Force"
if errorlevel 1 goto :fail

set /p "SHORTCUT=Create desktop shortcut? [Y/n]: "
if /I not "%SHORTCUT%"=="n" powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=$env:INSTALL_DIR; $ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\NEXO.lnk'); $s.TargetPath=Join-Path $d 'NEXO.exe'; $s.WorkingDirectory=$d; $s.Description='NEXO'; $s.Save()"

echo.
echo NEXO installed to: %INSTALL_DIR%
set /p "RUN=Launch NEXO now? [Y/n]: "
if /I not "%RUN%"=="n" start "" "%INSTALL_DIR%\NEXO.exe"
exit /b 0

:fail
echo Installation failed. Check internet connection and permissions.
pause
exit /b 1
