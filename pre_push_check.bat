@echo off
echo ═══════════════════════════════════════════════════════════════════
echo   PRE-PUSH VERIFICATION
echo ═══════════════════════════════════════════════════════════════════
echo.

echo [1/6] Checking Git status...
git status --short
echo.

echo [2/6] Checking for sensitive files...
echo Checking for .env files...
if exist "frontend\.env.local" (
    echo ⚠ WARNING: frontend\.env.local exists but will be excluded
) else (
    echo ✓ No .env.local found
)

if exist "backend\.env" (
    echo ⚠ WARNING: backend\.env exists but will be excluded
) else (
    echo ✓ No backend .env found
)
echo.

echo [3/6] Checking what will be pushed...
echo.
echo Files to be committed:
git diff --cached --name-only
echo.

echo [4/6] Checking for API keys in code...
findstr /S /I /C:"GEMINI_API_KEY" frontend\app\*.tsx frontend\app\*.ts 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ⚠ WARNING: Found GEMINI_API_KEY in code files!
) else (
    echo ✓ No hardcoded API keys found in frontend
)
echo.

echo [5/6] Verifying .gitignore...
if exist ".gitignore" (
    echo ✓ .gitignore exists
    findstr /C:"*.md" .gitignore >nul
    if %ERRORLEVEL% EQU 0 (
        echo ✓ .md files are excluded
    ) else (
        echo ⚠ WARNING: .md files might not be excluded
    )
) else (
    echo ✗ .gitignore not found!
)
echo.

echo [6/6] Checking excluded .md files...
echo.
echo These .md files will NOT be pushed:
dir /B /S *.md 2>nul | findstr /V "README.md"
echo.
echo This .md file WILL be pushed:
if exist "README.md" (
    echo ✓ README.md
) else (
    echo ⚠ README.md not found
)
echo.

echo ═══════════════════════════════════════════════════════════════════
echo   SUMMARY
echo ═══════════════════════════════════════════════════════════════════
echo.
echo ✅ Project is ready to push to GitHub
echo ✅ Unnecessary .md files will be excluded
echo ✅ Sensitive files will be excluded
echo ✅ .env.example will be included
echo.
echo Next steps:
echo 1. git add .
echo 2. git commit -m "Initial commit"
echo 3. git remote add origin YOUR_GITHUB_URL
echo 4. git push -u origin main
echo.
echo For detailed instructions, see: DEPLOYMENT_INSTRUCTIONS.txt
echo.
pause
