$ErrorActionPreference = 'Stop'
$runtimeRoot = Join-Path $PSScriptRoot '.runtime'
$downloadRoot = Join-Path $runtimeRoot 'downloads'
$destination = Join-Path $runtimeRoot 'ollama'
$version = 'v0.40.16'
$expectedSha256 = '50fcf5ad54277f2fa5d173ebfc93bcb017adbc0c9ef2314daabc96ca9e6aa64e'
$archive = Join-Path $downloadRoot 'ollama-windows-amd64.zip'
New-Item -ItemType Directory -Path $downloadRoot,$destination -Force | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $destination 'ollama.exe'))) {
    $ProgressPreference = 'SilentlyContinue'
    if (-not (Test-Path -LiteralPath $archive)) {
        Write-Host 'Downloading the official portable Ollama runtime (about 1.6 GB)...'
        Invoke-WebRequest -Uri "https://github.com/ollama/ollama/releases/download/$version/ollama-windows-amd64.zip" -OutFile $archive
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expectedSha256) {
        throw "Archive checksum mismatch. Remove the incomplete archive at $archive, then retry."
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $destination -Force
}
& (Join-Path $PSScriptRoot 'Start-Ollama.ps1') -PullModel
