# Sets up the local dev environment for this repo. Dot-source it in every shell:
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   . .\tools\dev_env.ps1
#
# It keeps every temp/cache path inside the repo (the DSH sandbox only allows
# writes under the workspace) and loads the sitecustomize shim that fixes the
# 0o700 temp-dir ACL problem described in docs/桌面应用.md.

$RepoRoot = Split-Path -Parent $PSScriptRoot

$env:PYTHONPATH = (Join-Path $RepoRoot '.tools\sitecustomize')
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TMP = (Join-Path $RepoRoot '.tmp')
$env:TEMP = $env:TMP
$env:TMPDIR = $env:TMP
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
$env:PIP_NO_CACHE_DIR = '1'
$env:APP_DATA_DIR = (Join-Path $RepoRoot '.tmp\appdata')
$env:PYTHONUTF8 = '1'

foreach ($dir in @($env:TMP, $env:APP_DATA_DIR)) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (Test-Path $VenvPython) {
    $env:PATH = (Join-Path $RepoRoot '.venv\Scripts') + ';' + $env:PATH
}

$global:RepoRoot = $RepoRoot
