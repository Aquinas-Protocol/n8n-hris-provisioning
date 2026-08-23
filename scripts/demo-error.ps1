# Demonstrate the error lane: arm the mock so the next 3 mutating Directory calls return 500
# (enough to exhaust the create node's 3 retries), then fire a fresh HRIS event.
# After you click Approve, the execution fails at "Google: create user" and #it-alerts gets a message.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
if (Test-Path "$Root\.env") {
  Get-Content "$Root\.env" | Where-Object { $_ -match '^\s*[^#\s][^=]*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), 'Process')
  }
}
$Mock = if ($env:GOOGLE_ADMIN_BASE_URL) { $env:GOOGLE_ADMIN_BASE_URL } else { 'http://localhost:8000' }

curl.exe -sS -X POST "$Mock/_mock/reset" | Out-Null
curl.exe -sS -X POST "$Mock/_mock/fail-next" -H 'Content-Type: application/json' -d '{"count":3,"status":500}'
Write-Host ''
& "$Root\scripts\fire-webhook.ps1"
