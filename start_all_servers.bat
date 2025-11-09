@echo off
echo ═══════════════════════════════════════════════════════════════════
echo   AI CAREER ADVISOR - STARTING ALL SERVERS
echo ═══════════════════════════════════════════════════════════════════
echo.

echo [1/2] Starting Python Backend...
echo.
start "AI Career Advisor - Backend" cmd /k "cd backend && python main.py"
timeout /t 3 /nobreak > nul

echo [2/2] Starting Next.js Frontend...
echo.
start "AI Career Advisor - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   SERVERS STARTING...
echo ═══════════════════════════════════════════════════════════════════
echo.
echo Backend will be available at:  http://localhost:5000
echo Frontend will be available at: http://localhost:3000
echo.
echo Two new terminal windows have been opened:
echo   1. Backend Terminal (Python FastAPI)
echo   2. Frontend Terminal (Next.js)
echo.
echo Wait for both servers to start, then open:
echo   http://localhost:3000
echo.
echo To test the upload functionality:
echo   1. Upload a resume (PDF or DOCX)
echo   2. Click "Upload Resume"
echo   3. You will be redirected to the Analysis page
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.
pause
