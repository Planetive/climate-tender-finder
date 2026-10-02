# PowerShell script to start the frontend server
Write-Host "Starting Frontend Server..." -ForegroundColor Green
Write-Host ""

# Change to frontend directory
$frontendPath = Join-Path $PSScriptRoot "frontend"
Set-Location $frontendPath

# Check if node_modules exists, if not install dependencies
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
    Write-Host ""
}

Write-Host "Starting frontend development server..." -ForegroundColor Green
Write-Host "Frontend will be available at: http://localhost:8080" -ForegroundColor Cyan
Write-Host ""

# Start the dev server
npm run dev
