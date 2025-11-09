@echo off
echo ═══════════════════════════════════════════════════════════════════
echo   TESTING UPLOAD FUNCTIONALITY
echo ═══════════════════════════════════════════════════════════════════
echo.

echo [Step 1] Checking if backend is running...
curl -s http://localhost:5000/health > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Backend is running on port 5000
    echo.
    curl http://localhost:5000/health
    echo.
) else (
    echo ✗ Backend is NOT running!
    echo.
    echo Please start the backend first:
    echo   cd backend
    echo   python main.py
    echo.
    pause
    exit /b 1
)

echo.
echo [Step 2] Checking if frontend is running...
curl -s http://localhost:3000 > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Frontend is running on port 3000
) else (
    echo ✗ Frontend is NOT running!
    echo.
    echo Please start the frontend:
    echo   cd frontend
    echo   npm run dev
    echo.
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   BOTH SERVERS ARE RUNNING!
echo ═══════════════════════════════════════════════════════════════════
echo.
echo Now test the upload:
echo   1. Open http://localhost:3000
echo   2. Upload a resume file
echo   3. Open browser console (F12) to see logs
echo   4. Check for these console messages:
echo      - "Uploading file to backend..."
echo      - "Response status: 200"
echo      - "Analysis data stored in localStorage"
echo      - "Redirecting to analysis page..."
echo.
echo If you see an error, check the console for details.
echo.
pause
