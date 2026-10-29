# Copies the desktop app and a source snapshot to another drive (default D:) and
# verifies the copied app actually starts.
#
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\tools\deploy_to_d.ps1                      # copy app + source snapshot to D:\
#   .\tools\deploy_to_d.ps1 -Mirror              # mirror instead of copy (removes stale files)
#   .\tools\deploy_to_d.ps1 -Drive E:            # another drive
#   .\tools\deploy_to_d.ps1 -SkipApp             # source only
#   .\tools\deploy_to_d.ps1 -NoVerify            # skip the startup probe
#
# Result:
#   <Drive>\GexingTuijian\             runnable app (portable data in .\data)
#   <Drive>\gexinghuatuijianxitong\    source + docs + tests + openspec
#
# Note: keep .venv / node_modules out of the copy. They contain absolute paths and
# must be recreated on the target machine with tools\setup_dev.ps1.

param(
    [string]$Drive = 'D:',
    [switch]$Mirror,
    [switch]$SkipApp,
    [switch]$NoVerify
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$AppSrc = Join-Path $Repo 'dist\GexingTuijian'
$AppDst = Join-Path "$Drive\" 'GexingTuijian'
$SrcDst = Join-Path "$Drive\" 'gexinghuatuijianxitong'
$Mode = if ($Mirror) { '/MIR' } else { '/E' }

if (-not (Test-Path "$Drive\")) { throw "drive $Drive not found" }

if (-not $SkipApp) {
    if (-not (Test-Path $AppSrc)) {
        throw "missing $AppSrc - run .\desktop\build.ps1 first"
    }
    Write-Host "==> copying app to $AppDst"
    New-Item -ItemType Directory -Force $AppDst | Out-Null
    robocopy $AppSrc $AppDst $Mode /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy app failed ($LASTEXITCODE)" }

    $launcher = "@echo off`r`ncd /d `"%~dp0`"`r`nstart `"`" `"GexingTuijian.exe`" --portable`r`n"
    Set-Content -Path (Join-Path $AppDst 'Start-portable.cmd') -Value $launcher -Encoding Default

    $readme = @'
# 个性化推荐系统 · 桌面版（D 盘副本）

## 怎么打开

双击 `Start-portable.cmd`（推荐，数据放在本目录 `data\`），或直接双击 `GexingTuijian.exe`。

- 演示账号：`demo` / `demo1234`，管理员 `admin` / `demo1234`
- 只监听 127.0.0.1，端口自动选（默认 8765）
- 内嵌窗口渲染不可用时，8 秒后会自动用系统浏览器打开同一地址

## 数据在哪

- 用 `Start-portable.cmd` 启动：数据在 `本目录\data\`（app.db / logs / secret.key）
- 直接双击 exe：数据在 `%LOCALAPPDATA%\GexingTuijian`
- 想换位置：`GexingTuijian.exe --data-dir E:\somewhere`

## 出问题看哪里

- `GexingTuijian-crash.log`（exe 同目录）
- `data\logs\app.log`、`data\logs\uvicorn.log`

## 源码在哪

同盘 `gexinghuatuijianxitong\`，重建开发环境：

```powershell
cd <盘>:\gexinghuatuijianxitong
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\tools\setup_dev.ps1
```
'@
    Set-Content -Path (Join-Path $AppDst 'README.md') -Value $readme -Encoding utf8
}

Write-Host "==> copying source snapshot to $SrcDst"
New-Item -ItemType Directory -Force $SrcDst | Out-Null
$excludeDirs = @('.venv', 'node_modules', 'build', '.tmp', '.data', '__pycache__', '.pytest_cache')
robocopy $Repo $SrcDst $Mode /XD @excludeDirs /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy source failed ($LASTEXITCODE)" }

$appSize = if (Test-Path $AppDst) {
    [math]::Round(((Get-ChildItem $AppDst -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 1)
} else { 0 }
$srcSize = [math]::Round(((Get-ChildItem $SrcDst -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host "==> app: $AppDst ($appSize MB)"
Write-Host "==> src: $SrcDst ($srcSize MB)"

if ($NoVerify -or $SkipApp) { return }

Write-Host '==> verifying the copied app starts'
$exe = Join-Path $AppDst 'GexingTuijian.exe'
$port = 8841
& $exe --portable --no-window --port $port | Out-Null
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/v1/health" -TimeoutSec 2
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if ($ready) {
    Write-Host "==> OK: health=$($health.status) items=$($health.items) events=$($health.events)"
    Write-Host "    data dir: $(Join-Path $AppDst 'data')"
} else {
    Write-Warning "copied app did not become healthy on port $port - check $(Join-Path $AppDst 'GexingTuijian-crash.log')"
}
