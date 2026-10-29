# Runs the desktop app from source (no packaging).
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\desktop\run_desktop.ps1                            # native window
#   .\desktop\run_desktop.ps1 -ExtraArgs '--no-window'   # headless smoke

param(
    [string[]]$ExtraArgs = @()
)

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. (Join-Path $PSScriptRoot '..\tools\dev_env.ps1')

$ErrorActionPreference = 'Continue'
Push-Location $RepoRoot
try {
    & python (Join-Path $PSScriptRoot 'main.py') @ExtraArgs 2>&1 | Write-Host
} finally {
    Pop-Location
}
