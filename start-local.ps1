# Start both halves of the local app. Reuse healthy services already running.
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtime = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$logRoot = Join-Path $projectRoot 'work\local-runtime'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Install the backend project environment first. See outputs/Materials_Implementation_Status.md.' }

function Test-LocalService([string]$Address) {
    try { return (Invoke-WebRequest -Uri $Address -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 }
    catch { return $false }
}

if (-not (Test-LocalService 'http://127.0.0.1:8000/health')) {
    $api = Start-Process -FilePath $runtime -ArgumentList @('-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot 'api.log') -RedirectStandardError (Join-Path $logRoot 'api-error.log')
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Test-LocalService 'http://127.0.0.1:8000/health') { $ready = $true; break }
        if ($api.HasExited) { break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "Tutor service did not start. See $logRoot\api-error.log" }
    Write-Host "Tutor service started (PID $($api.Id))."
}
if (-not (Test-LocalService 'http://localhost:3000/')) {
    $npm = (Get-Command npm.cmd).Source
    $ui = Start-Process -FilePath $npm -ArgumentList @('run', 'dev', '--', '--port', '3000') -WorkingDirectory (Join-Path $projectRoot 'web') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot 'web.log') -RedirectStandardError (Join-Path $logRoot 'web-error.log')
    Write-Host "Web interface starting (PID $($ui.Id)). Logs: $logRoot"
}
Write-Host 'Local app: http://localhost:3000'
