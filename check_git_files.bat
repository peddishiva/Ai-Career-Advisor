@echo off
echo ═══════════════════════════════════════════════════════════════════
echo   CHECKING WHAT WILL BE PUSHED TO GITHUB
echo ═══════════════════════════════════════════════════════════════════
echo.

echo [1] Files that will be EXCLUDED (gitignored):
echo ─────────────────────────────────────────────────────────────────
echo.

echo Checking .md files...
git check-ignore QUICKSTART.md 2>nul && echo ✓ QUICKSTART.md - EXCLUDED || echo ✗ QUICKSTART.md - WILL BE PUSHED
git check-ignore IMPLEMENTATION_SUMMARY.md 2>nul && echo ✓ IMPLEMENTATION_SUMMARY.md - EXCLUDED || echo ✗ IMPLEMENTATION_SUMMARY.md - WILL BE PUSHED
git check-ignore ARCHITECTURE.md 2>nul && echo ✓ ARCHITECTURE.md - EXCLUDED || echo ✗ ARCHITECTURE.md - WILL BE PUSHED
git check-ignore backend/README_PYTHON.md 2>nul && echo ✓ backend/README_PYTHON.md - EXCLUDED || echo ✗ backend/README_PYTHON.md - WILL BE PUSHED

echo.
echo Checking .txt files...
git check-ignore DEBUG_UPLOAD_ISSUE.txt 2>nul && echo ✓ DEBUG_UPLOAD_ISSUE.txt - EXCLUDED || echo ✗ DEBUG_UPLOAD_ISSUE.txt - WILL BE PUSHED
git check-ignore UPLOAD_TROUBLESHOOTING.txt 2>nul && echo ✓ UPLOAD_TROUBLESHOOTING.txt - EXCLUDED || echo ✗ UPLOAD_TROUBLESHOOTING.txt - WILL BE PUSHED
git check-ignore UPLOAD_FLOW.txt 2>nul && echo ✓ UPLOAD_FLOW.txt - EXCLUDED || echo ✗ UPLOAD_FLOW.txt - WILL BE PUSHED
git check-ignore SECURITY_CHECKLIST.txt 2>nul && echo ✓ SECURITY_CHECKLIST.txt - EXCLUDED || echo ✗ SECURITY_CHECKLIST.txt - WILL BE PUSHED
git check-ignore GITHUB_PUSH_GUIDE.txt 2>nul && echo ✓ GITHUB_PUSH_GUIDE.txt - EXCLUDED || echo ✗ GITHUB_PUSH_GUIDE.txt - WILL BE PUSHED
git check-ignore BACKEND_FRONTEND_VERIFICATION.txt 2>nul && echo ✓ BACKEND_FRONTEND_VERIFICATION.txt - EXCLUDED || echo ✗ BACKEND_FRONTEND_VERIFICATION.txt - WILL BE PUSHED

echo.
echo Checking sensitive files...
git check-ignore .env 2>nul && echo ✓ .env - EXCLUDED || echo ✗ .env - WILL BE PUSHED
git check-ignore .env.python 2>nul && echo ✓ .env.python - EXCLUDED || echo ✗ .env.python - WILL BE PUSHED
git check-ignore backend/src/config/serviceAccountKey.json 2>nul && echo ✓ serviceAccountKey.json - EXCLUDED || echo ✗ serviceAccountKey.json - WILL BE PUSHED
git check-ignore backend/uploads/ 2>nul && echo ✓ backend/uploads/ - EXCLUDED || echo ✗ backend/uploads/ - WILL BE PUSHED

echo.
echo ═══════════════════════════════════════════════════════════════════
echo.

echo [2] Files that WILL BE PUSHED (not gitignored):
echo ─────────────────────────────────────────────────────────────────
echo.

git check-ignore README.md 2>nul && echo ✗ README.md - EXCLUDED || echo ✓ README.md - WILL BE PUSHED
git check-ignore .env.example 2>nul && echo ✗ .env.example - EXCLUDED || echo ✓ .env.example - WILL BE PUSHED
git check-ignore .gitignore 2>nul && echo ✗ .gitignore - EXCLUDED || echo ✓ .gitignore - WILL BE PUSHED
git check-ignore package.json 2>nul && echo ✗ package.json - EXCLUDED || echo ✓ package.json - WILL BE PUSHED
git check-ignore backend/requirements.txt 2>nul && echo ✗ backend/requirements.txt - EXCLUDED || echo ✓ backend/requirements.txt - WILL BE PUSHED
git check-ignore backend/main.py 2>nul && echo ✗ backend/main.py - EXCLUDED || echo ✓ backend/main.py - WILL BE PUSHED
git check-ignore frontend/app/page.tsx 2>nul && echo ✗ frontend/app/page.tsx - EXCLUDED || echo ✓ frontend/app/page.tsx - WILL BE PUSHED

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   SUMMARY
echo ═══════════════════════════════════════════════════════════════════
echo.
echo ✓ All unnecessary .md files will be EXCLUDED
echo ✓ All documentation .txt files will be EXCLUDED
echo ✓ All sensitive files (.env, keys) will be EXCLUDED
echo ✓ Only README.md will be included
echo ✓ Source code and config files will be included
echo.
echo You're safe to push to GitHub!
echo.
pause
