@echo off
REM Quick Start Script for Glass Design Frontend (Windows)

echo.
echo 🚀 Glass Design Frontend - Quick Start
echo ======================================
echo.

REM Check Node.js
echo 📦 Checking Node.js installation...
where node >nul 2>nul
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✅ Node.js %NODE_VERSION% installed
echo.

REM Navigate to frontend_glass
echo 📂 Navigating to frontend_glass directory...
cd /d "%~dp0frontend_glass" || exit /b 1
echo ✅ In %cd%
echo.

REM Install dependencies
echo 📥 Installing dependencies...
call npm install
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed
echo.

REM Start dev server
echo 🎬 Starting development server...
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ✅ Server running at: http://localhost:5173
echo.
echo 📝 Important:
echo    • Backend must be running on http://localhost:8000
echo    • Open browser to http://localhost:5173
echo    • Changes auto-reload
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

call npm run dev
pause
