$ErrorActionPreference = 'Stop'
$runtimeRoot = Join-Path $PSScriptRoot '.runtime'
$pidFile = Join-Path $runtimeRoot 'ollama.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'No project server PID recorded.'; return }
$serverId = [int](Get-Content -LiteralPath $pidFile)
$expectedExe = Join-Path $runtimeRoot 'ollama\ollama.exe'
$server = Get-Process -Id $serverId -ErrorAction SilentlyContinue
if ($server -and $server.Path -eq $expectedExe) {
    Stop-Process -Id $serverId
    Write-Host 'Stopped the project Ollama service.'
} elseif ($server) {
    throw 'PID belongs to a different program; nothing was stopped.'
} else { Write-Host 'Project server is already stopped.' }
