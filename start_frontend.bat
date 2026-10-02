@echo off
echo Starting Frontend Server...
echo.
cd /d "%~dp0\frontend"
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)
echo.
echo Starting frontend development server...
call npm run dev
pause
