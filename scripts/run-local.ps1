# Native (no Docker) run: the mock Admin SDK in a background process + n8n 2.35.7 via npx in the foreground.
# Needs Node 20.19–24.x and Python 3.11+. Data lands in %USERPROFILE%\.n8n. Ctrl-C stops n8n; the mock is stopped on exit.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
if (Test-Path "$Root\.env") {
  Get-Content "$Root\.env" | Where-Object { $_ -match '^\s*[^#\s][^=]*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), 'Process')
  }
}
$env:N8N_BLOCK_ENV_ACCESS_IN_NODE = 'false'
if (-not $env:GOOGLE_ADMIN_BASE_URL) { $env:GOOGLE_ADMIN_BASE_URL = 'http://localhost:8000' }
if (-not $env:WEBHOOK_URL) { $env:WEBHOOK_URL = 'http://localhost:5678/' }
$env:N8N_WEBHOOK_URL = $env:WEBHOOK_URL
$env:N8N_DIAGNOSTICS_ENABLED = 'false'; $env:N8N_VERSION_NOTIFICATIONS_ENABLED = 'false'; $env:N8N_PERSONALIZATION_ENABLED = 'false'

$mock = Start-Process -FilePath python -ArgumentList "`"$Root\mock-google-admin\mock_google_admin.py`" --port 8000" -PassThru -NoNewWindow
try {
  npx -y n8n@2.35.7
} finally {
  if ($mock -and -not $mock.HasExited) { Stop-Process -Id $mock.Id -Force }
}
