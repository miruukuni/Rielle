param([switch]$PullModel, [string]$Model)
$ErrorActionPreference = 'Stop'
$runtimeRoot = Join-Path $PSScriptRoot '.runtime'
$exe = Join-Path $runtimeRoot 'ollama\ollama.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Portable runtime missing at $exe. See README.md." }
$config = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'character\config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$apiUrl = [uri]$config.runtime.base_url
if (-not $apiUrl.IsAbsoluteUri -or $apiUrl.Scheme -ne 'http' -or $apiUrl.Host -ne '127.0.0.1' -or $apiUrl.PathAndQuery -ne '/' -or $apiUrl.UserInfo -or $apiUrl.Fragment) {
    throw 'Set runtime.base_url to http://127.0.0.1:<port> in character/config.json.'
}
$env:OLLAMA_HOST = $apiUrl.Authority
$versionUrl = [uri]::new($apiUrl, '/api/version')
$env:OLLAMA_MODELS = Join-Path $runtimeRoot 'models'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$env:OLLAMA_FLASH_ATTENTION = '1'
New-Item -ItemType Directory -Path $env:OLLAMA_MODELS -Force | Out-Null
$existing = $null
try { $existing = Invoke-RestMethod -Uri $versionUrl -TimeoutSec 2 } catch {}
if ($existing) {
    Write-Host "A service is already running (version $($existing.version)). Its environment is unchanged."
} else {
    $server = Start-Process -FilePath $exe -ArgumentList 'serve' -WorkingDirectory $runtimeRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'ollama.stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'ollama.stderr.log')
    $server.Id | Set-Content -LiteralPath (Join-Path $runtimeRoot 'ollama.pid')
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        if ($server.HasExited) { throw 'Ollama stopped. Check .runtime/ollama.stderr.log.' }
        try { $null = Invoke-RestMethod -Uri $versionUrl -TimeoutSec 1; $ready = $true; break } catch {}
    }
    if (-not $ready) { throw 'Ollama did not become ready. Check .runtime/ollama.stderr.log.' }
    Write-Host 'Local Ollama is ready. Cloud features disabled; one model at a time.'
}
if ($PullModel) {
    if (-not $Model) { $Model = $config.runtime.model }
    & $exe pull $Model
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed. Re-run with -PullModel to resume.' }
}
