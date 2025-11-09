@echo off
echo ========================================
echo   AI Career Advisor - GitHub Push
echo ========================================
echo.

echo [1/5] Checking Git status...
git status
echo.

echo [2/5] Verifying sensitive files are gitignored...
echo.
echo Checking serviceAccountKey.json...
git check-ignore backend/src/config/serviceAccountKey.json
if %ERRORLEVEL% EQU 0 (
    echo ✓ serviceAccountKey.json is gitignored
) else (
    echo ✗ WARNING: serviceAccountKey.json might not be gitignored!
)

echo.
echo Checking .env files...
git check-ignore .env
if %ERRORLEVEL% EQU 0 (
    echo ✓ .env is gitignored
) else (
    echo ✗ WARNING: .env might not be gitignored!
)

echo.
echo Checking markdown files...
git check-ignore QUICKSTART.md
if %ERRORLEVEL% EQU 0 (
    echo ✓ QUICKSTART.md is gitignored
) else (
    echo ✗ WARNING: QUICKSTART.md might not be gitignored!
)

echo.
echo [3/5] Files to be committed:
git diff --cached --name-only
echo.

echo [4/5] Searching for potential API keys in staged files...
git diff --cached | findstr /I "AIzaSy GEMINI_API_KEY apiKey.*:" > nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✗✗✗ WARNING: Potential API keys found in staged files! ✗✗✗
    echo Please review your changes before pushing!
    echo.
    pause
    exit /b 1
) else (
    echo ✓ No obvious API keys detected in staged files
)

echo.
echo [5/5] Ready to push!
echo.
echo ========================================
echo   FINAL SECURITY CHECK
echo ========================================
echo.
echo Please verify:
echo   1. No .md files (except README.md) are staged
echo   2. No .env files are staged
echo   3. No serviceAccountKey.json is staged
echo   4. No API keys in the diff
echo.

set /p confirm="Do you want to proceed with git push? (yes/no): "
if /I "%confirm%"=="yes" (
    echo.
    echo Pushing to GitHub...
    git push
    echo.
    echo ✓ Push complete!
) else (
    echo.
    echo Push cancelled.
)

echo.
pause
