$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$backendRequirements = Join-Path $projectRoot 'backend\requirements.txt'
$webDirectory = Join-Path $projectRoot 'web'
$venvDirectory = Join-Path $projectRoot 'backend\.venv'
$python = Get-Command python -ErrorAction SilentlyContinue
$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue

if (-not $python) { throw 'Install Python 3.12 or newer, then run this script again.' }
if (-not $node -or -not $npm) { throw 'Install Node.js 22.13 or newer (npm is included), then run this script again.' }

$pythonVersionOutput = (& $python.Source --version 2>&1 | Out-String).Trim()
if ($pythonVersionOutput -notmatch 'Python\s+(\d+\.\d+)') { throw "Could not read the Python version: $pythonVersionOutput" }
if ([version]$Matches[1] -lt [version]'3.12') { throw 'Open Learn needs Python 3.12 or newer.' }

$nodeVersion = (& $node.Source --version).Trim().TrimStart('v')
if ([version]$nodeVersion -lt [version]'22.13') { throw 'Open Learn needs Node.js 22.13 or newer.' }

$runtime = Join-Path $venvDirectory 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtime)) {
    Write-Host 'Creating the local Python environment…'
    & $python.Source -m venv $venvDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}

$backendHash = (Get-FileHash -LiteralPath $backendRequirements -Algorithm SHA256).Hash
$backendStamp = Join-Path $venvDirectory '.open-learn-requirements-hash'
$installedBackendHash = if (Test-Path -LiteralPath $backendStamp) { (Get-Content -LiteralPath $backendStamp -Raw).Trim() } else { '' }
if ($installedBackendHash -ne $backendHash) {
    Write-Host 'Installing the local service…'
    & $runtime -m pip install -r $backendRequirements
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the local service dependencies.' }
    Set-Content -LiteralPath $backendStamp -Value $backendHash -NoNewline
}

$webLock = Join-Path $webDirectory 'package-lock.json'
$webHash = (Get-FileHash -LiteralPath $webLock -Algorithm SHA256).Hash
$webModules = Join-Path $webDirectory 'node_modules'
$webStamp = Join-Path $webModules '.open-learn-lock-hash'
$installedWebHash = if (Test-Path -LiteralPath $webStamp) { (Get-Content -LiteralPath $webStamp -Raw).Trim() } else { '' }
if (-not (Test-Path -LiteralPath $webModules) -or $installedWebHash -ne $webHash) {
    Write-Host 'Installing the web app…'
    Push-Location $webDirectory
    try {
        & $npm.Source ci
        if ($LASTEXITCODE -ne 0) { throw 'Could not install the web app dependencies.' }
    } finally {
        Pop-Location
    }
    Set-Content -LiteralPath $webStamp -Value $webHash -NoNewline
}

Write-Host 'Starting Open Learn…'
& (Join-Path $projectRoot 'start-local.ps1')
