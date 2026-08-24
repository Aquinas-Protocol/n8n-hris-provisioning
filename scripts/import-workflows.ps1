# Import (upsert) both workflows into n8n, then list them. -Publish publishes the main workflow
# from the CLI and restarts n8n so the production webhook goes live.
# Works against the compose stack if it is running, otherwise against a native n8n (npx).
param([switch]$Publish)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$running = (docker compose ps --status running --services 2>$null) -contains 'n8n'
if ($running) {
  $n8n = { param($a) docker compose exec -T n8n n8n @a }
  $inputDir = '/workflows'
} else {
  $n8n = { param($a) npx -y n8n@2.35.7 @a }
  $inputDir = "$Root\workflows"
}

& $n8n @('import:workflow', '--separate', "--input=$inputDir")
& $n8n @('list:workflow')

if ($Publish) {
  & $n8n @('publish:workflow', '--id=HRISPROVMAIN0001'); & $n8n @('publish:workflow', '--id=HRISPROVERROR001')
  if ($running) { docker compose restart n8n } else { Write-Host 'restart your native n8n to activate the webhook' }
}
