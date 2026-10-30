# Moves the DeepSeek Harness desktop app + its user data + the workspace to another
# drive, and points shortcuts / registry / DSH_HOME at the new location.
#
#   IMPORTANT: run this with DeepSeek Harness CLOSED. The app locks app.asar and its
#   session files, and the script refuses to run while it is up (override with -Force).
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\tools\move_dsh_to_d.ps1              # full move to D:
#   .\tools\move_dsh_to_d.ps1 -Drive E:    # another drive
#   .\tools\move_dsh_to_d.ps1 -SkipWorkspace   # program + data only
#   .\tools\move_dsh_to_d.ps1 -DryRun      # print the plan, touch nothing
#
# What ends up where (defaults):
#   <Drive>\DeepSeek Harness\            the program (about 1 GB)
#   <Drive>\DeepSeekHarnessData\        DSH_HOME: sessions, attachments, profiles,
#                                         credentials, runtimes (about 320 MB)
#   <Drive>\deepseek-harness\default-workspace\   the working copy (about 4.4 GB)
#
# Rollback: delete the user environment variable DSH_HOME and launch the old exe from
# %LOCALAPPDATA%\Programs\DeepSeek Harness (until you delete that folder, nothing is lost).

param(
    [string]$Drive = 'D:',
    [string]$ProgramDir = 'DeepSeek Harness',
    [string]$DataDir = 'DeepSeekHarnessData',
    [string]$WorkspaceDir = 'deepseek-harness\default-workspace',
    [switch]$SkipProgram,
    [switch]$SkipData,
    [switch]$SkipWorkspace,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Say([string]$Text) { Write-Host "==> $Text" }

if (-not (Test-Path "$Drive\")) { throw "drive $Drive not found" }

$running = Get-Process -Name 'DeepSeek Harness' -ErrorAction SilentlyContinue
if ($running -and -not $Force) {
    throw "DeepSeek Harness is still running (pid $($running.Id -join ', ')). Close it first, then rerun."
}

$programSrc = Join-Path $env:LOCALAPPDATA 'Programs\DeepSeek Harness'
$programDst = Join-Path "$Drive\" $ProgramDir
$dataSrc = Join-Path $env:USERPROFILE '.dsh'
$dataDst = Join-Path "$Drive\" $DataDir
$workspaceSrc = 'C:\Users\lenovo\Documents\deepseek-harness\default-workspace'
$workspaceDst = Join-Path "$Drive\" $WorkspaceDir

$plan = [ordered]@{
    'Program'  = "$programSrc  ->  $programDst"
    'DSH_HOME' = "$dataSrc  ->  $dataDst"
    'Workspace'= "$workspaceSrc  ->  $workspaceDst"
}
if ($SkipProgram)   { $plan.Remove('Program') }
if ($SkipData)      { $plan.Remove('DSH_HOME') }
if ($SkipWorkspace) { $plan.Remove('Workspace') }

Write-Host 'Plan:'
$plan.GetEnumerator() | ForEach-Object { Write-Host ("  {0,-9} {1}" -f $_.Key, $_.Value) }
if ($DryRun) { Say 'dry run, nothing changed'; return }

if ($plan.Contains('Program')) {
    if (-not (Test-Path $programSrc)) { throw "missing $programSrc" }
    Say "copying program to $programDst"
    robocopy $programSrc $programDst /E /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy program failed ($LASTEXITCODE)" }
}

if ($plan.Contains('DSH_HOME')) {
    if (-not (Test-Path $dataSrc)) { throw "missing $dataSrc" }
    Say "copying user data to $dataDst"
    robocopy $dataSrc $dataDst /E /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy data failed ($LASTEXITCODE)" }
    Say "setting user environment variable DSH_HOME=$dataDst"
    [Environment]::SetEnvironmentVariable('DSH_HOME', $dataDst, 'User')
    $env:DSH_HOME = $dataDst
}

if ($plan.Contains('Workspace')) {
    Say "copying workspace to $workspaceDst"
    robocopy $workspaceSrc $workspaceDst /E /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy workspace failed ($LASTEXITCODE)" }
}

function New-Shortcut([string]$Path, [string]$Target, [string]$WorkDir, [string]$Icon) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $Target
    $shortcut.WorkingDirectory = $WorkDir
    $shortcut.IconLocation = $Icon
    $shortcut.Description = 'DeepSeek Harness'
    $shortcut.Save()
}

if ($plan.Contains('Program')) {
    $exe = Join-Path $programDst 'DeepSeek Harness.exe'
    if (-not (Test-Path $exe)) { throw "copied program is missing $exe" }

    $shortcuts = @(
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'DeepSeek Harness.lnk'),
        (Join-Path ([Environment]::GetFolderPath('Programs')) 'DeepSeek Harness.lnk')
    )
    foreach ($shortcut in $shortcuts) {
        Say "repointing shortcut $shortcut"
        New-Shortcut -Path $shortcut -Target $exe -WorkDir $programDst -Icon $exe
    }

    Say 'updating the uninstall registry entry'
    $uninstall = Join-Path $programDst 'Uninstall DeepSeek Harness.exe'
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{7F2D1B5E-6C0B-4A5A-9A4E-1A5F0B4C0D01}'
    $found = $false
    Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue |
        ForEach-Object {
            $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
            if ($props.DisplayName -eq 'DeepSeek Harness' -and $props.InstallLocation) {
                Set-ItemProperty -Path $_.PSPath -Name 'InstallLocation' -Value $programDst
                Set-ItemProperty -Path $_.PSPath -Name 'UninstallString' -Value "`"$uninstall`" /currentuser"
                Set-ItemProperty -Path $_.PSPath -Name 'DisplayIcon' -Value $exe
                Write-Host "    patched $($_.PSPath)"
                $script:found = $true
            }
        }
    if (-not $found) { Write-Warning 'uninstall registry entry not found; Apps & features will still point to the old path' }
}

$note = @"
# DeepSeek Harness 已迁移到 $(Join-Path "$Drive\" $ProgramDir)

- 程序：$(Join-Path "$Drive\" $ProgramDir)\DeepSeek Harness.exe
- 用户数据（DSH_HOME）：$dataDst
- 工作区：$workspaceDst
- 桌面/开始菜单快捷方式已指向新位置；卸载项已改为新路径。

## 接下来

1. 双击桌面上的 **DeepSeek Harness**，确认能启动、历史会话还在（应该在 $dataDst\sessions）。
2. 在 DSH 里新建会话，把工作区选为 $workspaceDst。
3. 确认无误后再删除旧目录（这一步不做也不会丢数据）：
   - %LOCALAPPDATA%\Programs\DeepSeek Harness
   - %USERPROFILE%\.dsh
   - C:\Users\lenovo\Documents\deepseek-harness\default-workspace

## 回滚

删除用户环境变量 DSH_HOME（系统属性 → 环境变量），再用旧快捷方式/旧 exe 启动即可。

## 注意

- 自动更新仍可能把程序装回 %LOCALAPPDATA%\Programs\DeepSeek Harness；如果出现"更新后又回到 C 盘"，重跑一次本脚本（-SkipData -SkipWorkspace）。
- 迁移前请确认新版能正常用，旧目录先别删。
"@
$notePath = Join-Path "$Drive\" 'DeepSeekHarness-迁移说明.md'
Set-Content -Path $notePath -Value $note -Encoding utf8
Say "wrote $notePath"
Say 'done. launch from the new shortcut, then open the workspace on the new drive.'
