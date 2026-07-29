# Install TradeBot agent as a Windows service via NSSM.
# Run from an elevated PowerShell. Requires nssm.exe and a configured agent.env.

param(
    [Parameter(Mandatory = $true)][string]$NssmPath,
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [string]$ServiceName = "TradeBotAgent"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path $RepoRoot).Path
$envFile = Join-Path $RepoRoot "agent.env"
if (-not (Test-Path $envFile)) {
    throw "Missing $envFile — copy agent.env.example and set WEBAPP_URL + AGENT_TOKEN"
}

$logDir = Join-Path $RepoRoot "agent\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

& $NssmPath install $ServiceName $PythonExe
& $NssmPath set $ServiceName AppDirectory $RepoRoot
& $NssmPath set $ServiceName AppParameters "-m agent"
& $NssmPath set $ServiceName AppStdout (Join-Path $logDir "stdout.log")
& $NssmPath set $ServiceName AppStderr (Join-Path $logDir "stderr.log")
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Load KEY=VALUE from agent.env into service environment
$pairs = @()
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $pairs += $line
    }
}
if ($pairs.Count -gt 0) {
    & $NssmPath set $ServiceName AppEnvironmentExtra $pairs
}

Write-Host "Installed $ServiceName. Start with: nssm start $ServiceName"
