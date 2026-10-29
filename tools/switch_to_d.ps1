# Final switch after the copy: point DSH at the D: copies and (optionally) remove the old ones.
#
#   Run this with DeepSeek Harness CLOSED, from a normal PowerShell window:
#     Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#     D:\switch-dsh-to-d.ps1              # switch + ask before deleting old dirs
#     D:\switch-dsh-to-d.ps1 -Force       # switch + delete old dirs without asking
#     D:\switch-dsh-to-d.ps1 -KeepOld     # switch only, keep the old install
#     D:\switch-dsh-to-d.ps1 -RebuildEnv  # also recreate .venv/node_modules on D:
#
# Steps: verify the D: copies -> set user env DSH_HOME -> repoint shortcuts ->
# patch the uninstall registry entry -> (optionally) delete the old directories.

param(
    [string]$Drive = 'D:',
    [switch]$KeepOld,
    [switch]$Force,
    [switch]$RebuildEnv
)

$ErrorActionPreference = 'Stop'
$programDst = Join-Path "$Drive\" 'DeepSeek Harness'
$dataDst = Join-Path "$Drive\" 'DeepSeekHarnessData'
$workspaceDst = Join-Path "$Drive\" 'deepseek-harness\default-workspace'
$programOld = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness'
$dataOld = Join-Path $env:USERPROFILE '.dsh'
$workspaceOld = 'C:\Users\lenovo\Documents\deepseek-harness\default-workspace'

function Say([string]$Text) { Write-Host "==> $Text" }
function Confirm([string]$Question) {
    if ($Force) { return $true }
    $answer = Read-Host "$Question [y/N]"
    return $answer -match '^(y|yes|是)$'
}

$running = Get-Process -Name 'DeepSeek Harness' -ErrorAction SilentlyContinue
if ($running) { throw "DeepSeek Harness is still running (pid $($running.Id -join ', ')). Close it first." }

$exe = Join-Path $programDst 'DeepSeek Harness.exe'
if (-not (Test-Path $exe)) { throw "missing $exe - run tools\move_dsh_to_d.ps1 first" }
if (-not (Test-Path (Join-Path $dataDst 'sessions'))) { throw "missing $dataDst\sessions - data copy incomplete" }

Say "DSH_HOME -> $dataDst"
[Environment]::SetEnvironmentVariable('DSH_HOME', $dataDst, 'User')
$env:DSH_HOME = $dataDst

Say 'repointing shortcuts'
$shell = New-Object -ComObject WScript.Shell
foreach ($path in @(
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'DeepSeek Harness.lnk'),
        (Join-Path ([Environment]::GetFolderPath('Programs')) 'DeepSeek Harness.lnk')
    )) {
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $exe
    $shortcut.WorkingDirectory = $programDst
    $shortcut.IconLocation = $exe
    $shortcut.Description = 'DeepSeek Harness'
    $shortcut.Save()
    Write-Host "    $path"
}

Say 'patching the uninstall registry entry'
$uninstall = Join-Path $programDst 'Uninstall DeepSeek Harness.exe'
Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue |
    ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props.DisplayName -like 'DeepSeek Harness*' -and $props.InstallLocation) {
            Set-ItemProperty -Path $_.PSPath -Name 'InstallLocation' -Value $programDst
            Set-ItemProperty -Path $_.PSPath -Name 'UninstallString' -Value "`"$uninstall`" /currentuser"
            Set-ItemProperty -Path $_.PSPath -Name 'DisplayIcon' -Value $exe
            Write-Host "    $($_.PSPath)"
        }
    }

if ($RebuildEnv) {
    Say 'recreating the dev environment on D:'
    Push-Location (Join-Path $workspaceDst 'gexinghuatuijianxitong')
    try {
        if (Test-Path '.\tools\setup_dev.ps1') { & '.\tools\setup_dev.ps1' }
        $web = Join-Path (Get-Location) 'web'
        if (Test-Path $web) {
            Push-Location $web
            try { if (Get-Command npm -ErrorAction SilentlyContinue) { & npm install --ignore-scripts } }
            finally { Pop-Location }
        }
    } finally {
        Pop-Location
    }
}

if ($KeepOld) {
    Say 'old directories kept. Delete manually once the new install works:'
    Write-Host "    $programOld"
    Write-Host "    $dataOld"
    Write-Host "    $workspaceOld"
    return
}

$targets = @(
    @{ Path = $programOld; Label = 'old program' },
    @{ Path = $dataOld; Label = 'old DSH_HOME (.dsh)' },
    @{ Path = $workspaceOld; Label = 'old workspace' }
) | Where-Object { Test-Path $_.Path }

foreach ($target in $targets) {
    if (Confirm "Delete $($target.Label): $($target.Path)?") {
        try {
            Remove-Item -Recurse -Force $target.Path
            Write-Host "    deleted $($target.Path)"
        } catch {
            Write-Warning "could not delete $($target.Path): $($_.Exception.Message)"
        }
    }
}

Say 'done. Start DeepSeek Harness from the desktop shortcut.'
Say 'Open the workspace D:\deepseek-harness\default-workspace when creating a new session.'
