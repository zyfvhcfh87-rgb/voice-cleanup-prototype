$ErrorActionPreference = "Stop"

Write-Host "=== Building Voice Cleanup Prototype (onedir) ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Missing .venv\Scripts\python.exe"
}
if (-not (Test-Path "main.py")) {
    Write-Error "Missing main.py"
}

Write-Host "[1/4] Cleaning old build outputs..." -ForegroundColor Yellow
Remove-Item -Path "build", "dist", "VoiceCleanupPrototype.spec" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[2/4] Running PyInstaller..." -ForegroundColor Yellow
$qtConfPath = ".venv\Scripts\qt.conf"
$pluginJunction = ".venv\Lib\site-packages\plugins"
$pysidePlugins = ".venv\Lib\site-packages\PySide6\plugins"

try {
    @("[Paths]", "Prefix = ../Lib/site-packages/PySide6", "Plugins = plugins") | Set-Content -Path $qtConfPath
    if (Test-Path $pluginJunction) {
        cmd /c rmdir "$pluginJunction"
    }
    New-Item -ItemType Junction -Path $pluginJunction -Target (Resolve-Path $pysidePlugins) | Out-Null

    & .venv\Scripts\python.exe -m PyInstaller `
        --clean `
        --noconfirm `
        --onedir `
        --windowed `
        --name VoiceCleanupPrototype `
        --exclude-module PyQt5 `
        --exclude-module PyQt6 `
        --exclude-module PySide2 `
        --exclude-module PySide6.QtWebEngineCore `
        --exclude-module PySide6.QtWebEngineWidgets `
        --exclude-module PySide6.QtWebEngineQuick `
        main.py
}
finally {
    Remove-Item $qtConfPath -Force -ErrorAction SilentlyContinue
    if (Test-Path $pluginJunction) {
        cmd /c rmdir "$pluginJunction"
    }
}

Write-Host "[3/4] Copying external whisper.cpp tools..." -ForegroundColor Yellow
$destDir = "dist\VoiceCleanupPrototype"
if (-not (Test-Path $destDir)) {
    Write-Error "PyInstaller build directory was not created successfully."
}

$qtPlatformsSrc = ".venv\Lib\site-packages\PySide6\plugins\platforms"
$qtPlatformsDest = "$destDir\_internal\PySide6\plugins\platforms"
if (-not (Test-Path "$qtPlatformsSrc\qwindows.dll")) {
    Write-Error "Missing PySide6 qwindows.dll at $qtPlatformsSrc"
}
New-Item -ItemType Directory -Force -Path $qtPlatformsDest | Out-Null
Copy-Item "$qtPlatformsSrc\*.dll" $qtPlatformsDest -Force

if (-not (Test-Path "tools\whisper.cpp\whisper-cli.exe")) {
    Write-Error "Missing tools\whisper.cpp\whisper-cli.exe"
}
if (-not (Test-Path "tools\whisper.cpp\models\ggml-base.bin")) {
    Write-Error "Missing tools\whisper.cpp\models\ggml-base.bin"
}

New-Item -ItemType Directory -Force -Path "$destDir\tools\whisper.cpp\models" | Out-Null
Copy-Item "tools\whisper.cpp\whisper-cli.exe" "$destDir\tools\whisper.cpp\" -Force
Copy-Item "tools\whisper.cpp\*.dll" "$destDir\tools\whisper.cpp\" -Force
Copy-Item "tools\whisper.cpp\models\ggml-*.bin" "$destDir\tools\whisper.cpp\models\" -Force

Write-Host "[4/4] Done." -ForegroundColor Yellow
Write-Host "Built: $destDir\VoiceCleanupPrototype.exe" -ForegroundColor Green
