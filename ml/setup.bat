@echo off
REM ML Training Setup Script for Windows

echo ==========================================
echo Washing Machine ML - Training Setup
echo ==========================================

REM Check Python version
echo.
echo Checking Python version...
python --version

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ==========================================
echo Setup complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Data is already copied from power_log_gus.csv
echo.
echo 2. Activate environment:
echo    venv\Scripts\activate
echo.
echo 3. Prepare data:
echo    python training\prepare_data.py
echo.
echo 4. Train model:
echo    python training\train_random_forest.py
echo.
pause
