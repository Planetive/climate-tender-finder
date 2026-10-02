@echo off
echo Starting News Tracker Backend Server...
echo.

REM Set Google Gemini API Key (if not already set)
REM Prefer: set GEMINI_API_KEY in your environment, or create a local .env (not committed)
if "%GEMINI_API_KEY%"=="" (
    echo WARNING: GEMINI_API_KEY is not set. AI filtering will be disabled.
    echo Set it with: set GEMINI_API_KEY=your-key-here
    echo.
)

cd /d "%~dp0"

REM Prefer Python 3.13 (has crawl4ai); fall back to default python
py -3.13 -c "import crawl4ai" >nul 2>&1
if not errorlevel 1 (
    echo Using Python 3.13 with crawl4ai...
    py -3.13 main.py
) else (
    echo Using default python...
    python main.py
)
pause
