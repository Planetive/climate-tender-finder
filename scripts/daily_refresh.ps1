# Windows Task Scheduler helper — hits the same endpoint as "Re-run feeds"
# Schedule daily 07:00 Pakistan time (or your server local time).
# Example:
#   powershell -File "C:\path\to\scripts\daily_refresh.ps1"

$ApiBase = if ($env:API_BASE) { $env:API_BASE } else { "http://127.0.0.1:3001/api" }
$Url = "$ApiBase/feeds/refresh"
Write-Host "$(Get-Date -Format o) POST $Url"
try {
  $res = Invoke-RestMethod -Method Post -Uri $Url -TimeoutSec 7200
  $res | ConvertTo-Json -Depth 6
  Write-Host "$(Get-Date -Format o) done success=$($res.success)"
} catch {
  Write-Error $_
  exit 1
}
