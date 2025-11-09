@echo off
echo ═══════════════════════════════════════════════════════════════════
echo   FIXING 404 ERROR - Job Recommendations
echo ═══════════════════════════════════════════════════════════════════
echo.

echo [Diagnostic] Checking if routes are registered...
python test_backend_routes.py
echo.

echo ═══════════════════════════════════════════════════════════════════
echo   CAUSE OF 404 ERROR
echo ═══════════════════════════════════════════════════════════════════
echo.
echo The /api/jobs/recommendations endpoint was recently added.
echo.
echo If you're getting a 404 error, it means:
echo   1. The backend server is running with OLD code
echo   2. The server needs to be RESTARTED to load the new routes
echo.

echo ═══════════════════════════════════════════════════════════════════
echo   SOLUTION
echo ═══════════════════════════════════════════════════════════════════
echo.

echo STEP 1: Stop the old backend server
echo ─────────────────────────────────────────────────────────────────
echo   1. Find the terminal window running the backend
echo   2. Press Ctrl+C to stop it
echo   3. Close that terminal window
echo.

echo STEP 2: Start the backend with new code
echo ─────────────────────────────────────────────────────────────────
set /p START="Do you want to start the backend now? (y/n): "
if /i "%START%"=="y" (
    echo.
    echo Starting backend with new routes...
    echo.
    
    REM Check if GEMINI_API_KEY is set
    if not defined GEMINI_API_KEY (
        echo ⚠ WARNING: GEMINI_API_KEY is not set!
        echo.
        echo You need to set your Gemini API key first.
        echo Get your key from: https://makersuite.google.com/app/apikey
        echo.
        echo Then run:
        echo   PowerShell: $env:GEMINI_API_KEY="your-api-key-here"
        echo   CMD: set GEMINI_API_KEY=your-api-key-here
        echo.
        set /p CONTINUE="Continue without API key? (y/n): "
        if /i not "%CONTINUE%"=="y" (
            pause
            exit /b 1
        )
    )
    
    echo.
    echo Starting backend in new window...
    start "AI Career Advisor - Backend (NEW)" cmd /k "cd backend && python main.py"
    echo.
    echo ✓ Backend is starting with new routes...
    echo   Wait 5-10 seconds for it to fully start
    echo.
    timeout /t 8 /nobreak > nul
    echo.
    echo Testing backend...
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:5000/health' -UseBasicParsing; Write-Host '✓ Backend is running!' } catch { Write-Host '✗ Backend failed to start. Check the backend window for errors.' }"
    echo.
    echo Testing jobs endpoint...
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:5000/api/jobs/recommendations?query=test' -UseBasicParsing; Write-Host '✓ Jobs endpoint is working!' } catch { Write-Host '✗ Jobs endpoint returned error. Check backend window.' }"
)

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   VERIFICATION
echo ═══════════════════════════════════════════════════════════════════
echo.
echo Test these URLs in your browser:
echo.
echo 1. Backend health:
echo    http://localhost:5000/health
echo    Expected: {"status":"ok","service":"AI Career Advisor Backend"}
echo.
echo 2. Jobs API:
echo    http://localhost:5000/api/jobs/recommendations?query=software%%20engineer
echo    Expected: JSON with job listings
echo.
echo 3. Frontend:
echo    http://localhost:3000
echo    Search for a job and it should work!
echo.

echo ═══════════════════════════════════════════════════════════════════
echo   NEXT STEPS
echo ═══════════════════════════════════════════════════════════════════
echo.
echo 1. Make sure frontend is running: npm run dev
echo 2. Refresh your browser
echo 3. Try searching for jobs again
echo 4. Should see AI-generated job recommendations!
echo.
pause
