@echo off
echo ═══════════════════════════════════════════════════════════════════
echo   FIXING JOB RECOMMENDATIONS ERROR
echo ═══════════════════════════════════════════════════════════════════
echo.

echo [Diagnostic] Checking backend status...
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5000/health' -UseBasicParsing | Out-Null; Write-Host '✓ Backend is running' } catch { Write-Host '✗ Backend is NOT running' }"
echo.

echo [Diagnostic] Checking if GEMINI_API_KEY is set...
if defined GEMINI_API_KEY (
    echo ✓ GEMINI_API_KEY is set
) else (
    echo ✗ GEMINI_API_KEY is NOT set
    echo.
    echo You need to set your Gemini API key!
    echo.
    echo Get your key from: https://makersuite.google.com/app/apikey
    echo.
    echo Then run ONE of these commands:
    echo.
    echo PowerShell:
    echo   $env:GEMINI_API_KEY="your-api-key-here"
    echo.
    echo Command Prompt:
    echo   set GEMINI_API_KEY=your-api-key-here
    echo.
    pause
)

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   SOLUTION
echo ═══════════════════════════════════════════════════════════════════
echo.

echo The backend is not running. You need to start it!
echo.
echo Option 1: Start backend manually
echo ─────────────────────────────────────────────────────────────────
echo   1. Open a new terminal
echo   2. cd backend
echo   3. python main.py
echo.

echo Option 2: Use the startup script
echo ─────────────────────────────────────────────────────────────────
echo   Run: start_all_servers.bat
echo.

echo Option 3: Start backend now (in new window)
echo ─────────────────────────────────────────────────────────────────
set /p START="Do you want to start the backend now? (y/n): "
if /i "%START%"=="y" (
    echo.
    echo Starting backend in new window...
    start "AI Career Advisor - Backend" cmd /k "cd backend && python main.py"
    echo.
    echo ✓ Backend is starting...
    echo   Wait 5-10 seconds for it to fully start
    echo.
    timeout /t 5 /nobreak > nul
    echo.
    echo Testing backend...
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:5000/health' -UseBasicParsing; Write-Host '✓ Backend is now running!'; $response.Content } catch { Write-Host '✗ Backend failed to start. Check the backend window for errors.' }"
)

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   AFTER BACKEND STARTS
echo ═══════════════════════════════════════════════════════════════════
echo.
echo 1. Make sure frontend is running (npm run dev)
echo 2. Refresh your browser
echo 3. Try searching for jobs again
echo.
echo If you still get errors:
echo   - Check backend terminal for error messages
echo   - Verify GEMINI_API_KEY is set
echo   - Check browser console (F12) for errors
echo.
pause
