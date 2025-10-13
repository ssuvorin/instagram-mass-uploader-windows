@echo off
echo Installing FFmpeg for Windows...
echo ================================

REM Check if FFmpeg is already installed
ffmpeg -version >nul 2>&1
if %errorlevel% == 0 (
    echo FFmpeg is already installed!
    ffmpeg -version | findstr "ffmpeg version"
    pause
    exit /b 0
)

echo FFmpeg not found, installing...

REM Try WinGet first
echo Trying WinGet installation...
winget install Gyan.FFmpeg >nul 2>&1
if %errorlevel% == 0 (
    echo FFmpeg installed successfully via WinGet!
    goto :check_install
)

REM Try Chocolatey
echo Trying Chocolatey installation...
choco install ffmpeg -y >nul 2>&1
if %errorlevel% == 0 (
    echo FFmpeg installed successfully via Chocolatey!
    goto :check_install
)

REM Manual download
echo Downloading FFmpeg manually...
python install_ffmpeg_windows.py
if %errorlevel% == 0 (
    goto :check_install
)

echo Failed to install FFmpeg automatically.
echo Please install manually from https://ffmpeg.org/download.html
pause
exit /b 1

:check_install
echo Checking installation...
ffmpeg -version >nul 2>&1
if %errorlevel% == 0 (
    echo SUCCESS: FFmpeg is now installed and working!
    ffmpeg -version | findstr "ffmpeg version"
) else (
    echo WARNING: FFmpeg installed but not found in PATH
    echo Please restart your terminal or add FFmpeg to PATH manually
)

pause