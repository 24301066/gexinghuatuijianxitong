# Builds .venv and installs requirements.txt (idempotent).
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\tools\setup_dev.ps1            # create venv + install
#   .\tools\setup_dev.ps1 -Force     # recreate the venv from scratch
#
# Why this script exists: `python -m venv` and pip both create 0o700 temp dirs,
# which the DSH sandbox token cannot write into on this machine. dev_env.ps1
# redirects TMP/TEMP into the repo and enables the sitecustomize shim; sdist
# builds additionally need --no-build-isolation so the shim is visible to the
# build backend as well.

param(
    [switch]$Force,
    [switch]$SkipDesktop
)

$ErrorActionPreference = 'Stop'
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. (Join-Path $PSScriptRoot 'dev_env.ps1')

$Venv = Join-Path $RepoRoot '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'

if ($Force -and (Test-Path $Venv)) {
    Remove-Item -Recurse -Force $Venv
}

if (-not (Test-Path $Python)) {
    Write-Host "==> creating $Venv"
    # --without-pip: the venv builder runs ensurepip with a cleaned environment,
    # which loses the sitecustomize shim and dies on the 0o700 temp dir.
    python -m venv --without-pip $Venv
    if (-not (Test-Path $Python)) { throw "venv creation failed" }
    Write-Host "==> bootstrapping pip inside venv"
    & $Python -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) { throw "ensurepip failed" }
}

Write-Host "==> upgrading pip bootstrap"
& $Python -m pip install --disable-pip-version-check --no-cache-dir setuptools wheel 2>&1 | Select-Object -Last 2

$requirements = Join-Path $RepoRoot 'requirements.txt'
Write-Host "==> installing $requirements"
& $Python -m pip install --disable-pip-version-check --no-cache-dir --no-build-isolation -r $requirements 2>&1 | Select-Object -Last 5

if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

if (-not $SkipDesktop) {
    Write-Host "==> desktop deps"
    & $Python -m pip install --disable-pip-version-check --no-cache-dir --no-build-isolation -r (Join-Path $RepoRoot 'requirements-desktop.txt') 2>&1 | Select-Object -Last 5
}

Write-Host "==> versions"
& $Python -c "import sys, fastapi, sqlalchemy, numpy; print('python', sys.version.split()[0]); print('fastapi', fastapi.__version__); print('sqlalchemy', sqlalchemy.__version__); print('numpy', numpy.__version__)"
