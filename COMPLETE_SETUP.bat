@echo off
echo ═══════════════════════════════════════════════════════════════════
echo   AI CAREER ADVISOR - COMPLETE SETUP
echo ═══════════════════════════════════════════════════════════════════
echo.
echo This script will set up both backend and frontend.
echo.
pause

REM ═══════════════════════════════════════════════════════════════════
echo.
echo ═══════════════════════════════════════════════════════════════════
echo   PART 1: BACKEND SETUP
echo ═══════════════════════════════════════════════════════════════════
echo.

cd backend

echo [1/5] Checking Python...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Python not found!
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo ✓ Python found
echo.

echo [2/5] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo ✓ Created
) else (
    echo ✓ Already exists
)
echo.

echo [3/5] Installing Python dependencies...
call venv\Scripts\activate.bat
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed
echo.

echo [4/5] Creating directories...
if not exist "uploads" mkdir uploads
if not exist "uploads\analysis" mkdir uploads\analysis
echo ✓ Directories created
echo.

echo [5/5] Verifying backend files...
if exist "main.py" (echo ✓ main.py) else (echo ✗ main.py MISSING)
if exist "routes\upload.py" (echo ✓ routes\upload.py) else (echo ✗ routes\upload.py MISSING)
if exist "services\parser_service.py" (echo ✓ services\parser_service.py) else (echo ✗ services\parser_service.py MISSING)
echo.

cd ..

REM ═══════════════════════════════════════════════════════════════════
echo.
echo ═══════════════════════════════════════════════════════════════════
echo   PART 2: FRONTEND SETUP
echo ═══════════════════════════════════════════════════════════════════
echo.

cd frontend

echo [1/3] Checking Node.js...
node --version
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Node.js not found!
    echo Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)
echo ✓ Node.js found
echo.

echo [2/3] Installing Node dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed
echo.

echo [3/3] Verifying frontend files...
if exist "app\page.tsx" (echo ✓ app\page.tsx) else (echo ✗ app\page.tsx MISSING)
if exist "app\analysis\page.tsx" (echo ✓ app\analysis\page.tsx) else (echo ✗ app\analysis\page.tsx MISSING)
echo.

cd ..

REM ═══════════════════════════════════════════════════════════════════
echo.
echo ═══════════════════════════════════════════════════════════════════
echo   SETUP COMPLETE!
echo ═══════════════════════════════════════════════════════════════════
echo.
echo ✓ Backend is ready
echo ✓ Frontend is ready
echo.
echo ═══════════════════════════════════════════════════════════════════
echo   NEXT STEPS
echo ═══════════════════════════════════════════════════════════════════
echo.
echo 1. Start the backend:
echo    cd backend
echo    python main.py
echo.
echo 2. Start the frontend (in a new terminal):
echo    cd frontend
echo    npm run dev
echo.
echo 3. Open your browser:
echo    http://localhost:3000
echo.
echo 4. Upload a resume and test!
echo.
echo ═══════════════════════════════════════════════════════════════════
echo   QUICK START (AUTOMATED)
echo ═══════════════════════════════════════════════════════════════════
echo.
echo Or simply run: start_all_servers.bat
echo.
pause
