# PowerShell script to start the backend server
Write-Host "Starting News Tracker Backend Server..." -ForegroundColor Green
Write-Host ""

# Change to project root directory
Set-Location $PSScriptRoot

# Set Google Gemini API Key (if not already set)
# Prefer setting GEMINI_API_KEY in your environment (do not commit secrets)
if (-not $env:GEMINI_API_KEY) {
    Write-Host "WARNING: GEMINI_API_KEY is not set. AI filtering will be disabled." -ForegroundColor Yellow
    Write-Host 'Set it with: $env:GEMINI_API_KEY="your-key-here"' -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Backend will be available at: http://localhost:3001" -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:3001/docs" -ForegroundColor Cyan
Write-Host ""

# Prefer Python 3.13 when available (crawl4ai is installed there)
$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $py313 = & py -3.13 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $py313) {
        $pythonCmd = $py313.Trim()
    }
}
if (-not $pythonCmd) {
    $pythonCmd = "python"
}

Write-Host "Using Python: $pythonCmd" -ForegroundColor DarkGray
& $pythonCmd main.py
