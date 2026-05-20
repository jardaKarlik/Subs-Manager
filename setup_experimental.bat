@echo off
REM Quick setup for experimental branch

echo ========================================
echo EXPERIMENTAL BRANCH SETUP
echo ========================================
echo.

cd C:\_dev\subscription_manager

echo Creating experimental branch...
git checkout -b experimental/local-db-output 2>nul

if %errorlevel% neq 0 (
    echo Branch already exists, switching to it...
    git checkout experimental/local-db-output
)

echo.
echo ========================================
echo BRANCH READY: experimental/local-db-output
echo ========================================
echo.
echo Key changes:
echo   - Threshold: 0.25 (more matches)
echo   - Body: First 5 sentences (better context)
echo   - Sequential batches (no race condition)
echo.
echo To run experiment:
echo   python test_experimental.py
echo.
echo Data saves to:
echo   - experimental_subscriptions.db
echo   - experimental_results/
echo.
echo To return to main:
echo   git checkout main
echo.
pause
