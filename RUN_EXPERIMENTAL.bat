@echo off
REM Change to the script directory first
cd /d "%~dp0"

echo ========================================
echo EXPERIMENTAL TEST RUNNER
echo ========================================
echo.
echo Current directory: %cd%
echo.
echo This will:
echo   1. Create experimental branch
echo   2. Run test with relaxed parser
echo   3. Save to experimental_subscriptions.db
echo.
pause

REM Run the Python setup script from correct directory
python run_experimental.py

pause
