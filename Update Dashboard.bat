@echo off
echo ============================================================
echo CANVAS ASSIGNMENT DASHBOARD
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if config exists
if not exist config.py (
    echo config.py not found! Running setup...
    echo.
    python setup.py
    echo.
    pause
    exit
)

echo Updating your dashboard...
python all_courses_dashboard.py

if errorlevel 1 (
    echo.
    echo Something went wrong. Check the error above.
    pause
)
