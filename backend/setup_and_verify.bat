@echo off
echo ═══════════════════════════════════════════════════════════════════
echo   BACKEND SETUP AND VERIFICATION
echo ═══════════════════════════════════════════════════════════════════
echo.

echo [Step 1/6] Checking Python installation...
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
python --version
echo ✓ Python is installed
echo.

echo [Step 2/6] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)
echo.

echo [Step 3/6] Activating virtual environment...
call venv\Scripts\activate.bat
echo ✓ Virtual environment activated
echo.

echo [Step 4/6] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ All dependencies installed
echo.

echo [Step 5/6] Creating required directories...
if not exist "uploads" mkdir uploads
if not exist "uploads\analysis" mkdir uploads\analysis
echo ✓ Directories created
echo.

echo [Step 6/6] Verifying backend structure...
echo.
echo Checking required files:

if exist "main.py" (
    echo ✓ main.py
) else (
    echo ✗ main.py MISSING
)

if exist "routes\upload.py" (
    echo ✓ routes\upload.py
) else (
    echo ✗ routes\upload.py MISSING
)

if exist "routes\analysis.py" (
    echo ✓ routes\analysis.py
) else (
    echo ✗ routes\analysis.py MISSING
)

if exist "services\parser_service.py" (
    echo ✓ services\parser_service.py
) else (
    echo ✗ services\parser_service.py MISSING
)

if exist "services\analysis_service.py" (
    echo ✓ services\analysis_service.py
) else (
    echo ✗ services\analysis_service.py MISSING
)

if exist "utils\scoring_logic.py" (
    echo ✓ utils\scoring_logic.py
) else (
    echo ✗ utils\scoring_logic.py MISSING
)

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   SETUP COMPLETE!
echo ═══════════════════════════════════════════════════════════════════
echo.
echo Backend is ready to run.
echo.
echo To start the server:
echo   python main.py
echo.
echo The server will run on: http://localhost:5000
echo.
pause
