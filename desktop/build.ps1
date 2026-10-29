# Builds the Windows desktop package (one-folder + zip).
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\desktop\build.ps1                 # build web assets, then PyInstaller, then zip
#   .\desktop\build.ps1 -SkipWeb        # reuse the existing web/dist
#   .\desktop\build.ps1 -NoZip          # skip the zip step
#
# Output: dist/GexingTuijian/GexingTuijian.exe (+ _internal) and dist/GexingTuijian-<ver>.zip

param(
    [switch]$SkipWeb,
    [switch]$NoZip
)

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. (Join-Path $PSScriptRoot '..\tools\dev_env.ps1')

# Native tools write progress to stderr; keep that from aborting the script and
# rely on $LASTEXITCODE instead.
$ErrorActionPreference = 'Continue'

$Version = '0.1.0'
$DistExe = Join-Path $RepoRoot "dist\GexingTuijian\GexingTuijian.exe"

if (-not $SkipWeb) {
    Write-Host '==> building web assets'
    Push-Location (Join-Path $RepoRoot 'web')
    try {
        & npm run build 2>&1 | Write-Host
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) { throw 'npm run build failed' }
}

Write-Host '==> running PyInstaller'
& python -m PyInstaller (Join-Path $PSScriptRoot 'app.spec') --noconfirm `
    --distpath (Join-Path $RepoRoot 'dist') `
    --workpath (Join-Path $RepoRoot 'build\desktop') 2>&1 | Write-Host
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
if (-not (Test-Path $DistExe)) { throw "missing $DistExe" }

$SizeMb = [math]::Round(((Get-ChildItem (Split-Path $DistExe) -Recurse -File |
    Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host "==> dist/GexingTuijian ready ($SizeMb MB)"

if (-not $NoZip) {
    $Zip = Join-Path $RepoRoot "dist\GexingTuijian-${Version}.zip"
    if (Test-Path $Zip) { Remove-Item $Zip -Force }
    Write-Host '==> zipping'
    Compress-Archive -Path (Join-Path $RepoRoot 'dist\GexingTuijian\*') -DestinationPath $Zip
    $ZipMb = [math]::Round((Get-Item $Zip).Length / 1MB, 1)
    Write-Host "==> $Zip ($ZipMb MB)"
}

Write-Host ''
Write-Host "Run: $DistExe"
