# Fire one mock HRIS "employee.hired" event at the published workflow's webhook.
# Uses samples\new-hire.local.json if you made one (gitignored), else samples\new-hire.json.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
if (Test-Path "$Root\.env") {
  Get-Content "$Root\.env" | Where-Object { $_ -match '^\s*[^#\s][^=]*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), 'Process')
  }
}
$Payload = "$Root\samples\new-hire.local.json"
if (-not (Test-Path $Payload)) { $Payload = "$Root\samples\new-hire.json" }
$Base = if ($env:WEBHOOK_URL) { $env:WEBHOOK_URL } else { 'http://localhost:5678/' }
$Url = $Base.TrimEnd('/') + '/webhook/hris/new-hire'
if (-not $env:HRIS_WEBHOOK_TOKEN) { throw 'set HRIS_WEBHOOK_TOKEN in .env' }

Write-Host "POST $Url  ($(Split-Path -Leaf $Payload))"
curl.exe -sS -X POST $Url -H 'Content-Type: application/json' -H "X-HRIS-Token: $env:HRIS_WEBHOOK_TOKEN" --data-binary "@$Payload"
Write-Host ''
