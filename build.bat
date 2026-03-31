@echo off
setlocal

echo ============================================================
echo  BPSR Fishing Bot -- Build Script
echo ============================================================
echo.

REM ── Check Python ────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Make sure Python is in your PATH.
    pause & exit /b 1
)

REM ── Install / upgrade PyInstaller ───────────────────────────
echo [1/3] Installing PyInstaller...
pip install --quiet --upgrade pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause & exit /b 1
)

REM ── Install project dependencies ────────────────────────────
echo [2/3] Installing project dependencies...
pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.
    pause & exit /b 1
)

REM ── Run PyInstaller ─────────────────────────────────────────
echo [3/3] Building executable...
pyinstaller build.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above for details.
    pause & exit /b 1
)

echo.
echo ============================================================
echo  Build complete!
echo  Output: dist\BPSR-Fishing-Bot.exe
echo ============================================================
echo.

REM ── Open the output folder ──────────────────────────────────
explorer dist

pause
endlocal
