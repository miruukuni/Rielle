$ErrorActionPreference = 'Stop'
$model = 'hf.co/TheDrummer/Rocinante-X-12B-v1-GGUF:Q4_K_M'
& (Join-Path $PSScriptRoot 'Start-Ollama.ps1')

$config = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'character\config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$apiUrl = [uri]$config.runtime.base_url
$env:OLLAMA_HOST = $apiUrl.Authority
$installedModels = (Invoke-RestMethod -Uri ([uri]::new($apiUrl, '/api/tags')) -TimeoutSec 5).models.name
if ($model -notin $installedModels) {
    & (Join-Path $PSScriptRoot 'Start-Ollama.ps1') -PullModel -Model $model
}

$ollama = Join-Path $PSScriptRoot '.runtime\ollama\ollama.exe'
& $ollama create rielle-rocinante -f (Join-Path $PSScriptRoot 'Modelfile.Rocinante')
if ($LASTEXITCODE -ne 0) { throw 'Could not build the local Rocinante chat profile.' }
