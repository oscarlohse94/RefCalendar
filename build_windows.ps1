$ErrorActionPreference = "Stop"

$rootDir = $PSScriptRoot
$python = Join-Path $rootDir ".venv\Scripts\python.exe"
$oauthConfig = Join-Path $rootDir "credentials.json"
$distributionDir = Join-Path $rootDir "dist\RefCalendar"

if (-not (Test-Path $python)) {
    throw "Python-Umgebung fehlt. Richte zuerst .venv ein und installiere die Packaging-Abhängigkeit."
}
& $python -c "import PyInstaller" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller fehlt. Installiere es mit: py -3 -m pip --python .venv\Scripts\python.exe install -e `".[packaging]`""
}
if (-not (Test-Path $oauthConfig)) {
    throw "credentials.json fehlt. Für den Build wird ein Google-OAuth-Client vom Typ Desktop-App benötigt."
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name RefCalendar `
    --paths (Join-Path $rootDir "python") `
    --distpath (Join-Path $rootDir "dist") `
    --workpath (Join-Path $rootDir "build\pyinstaller") `
    --specpath (Join-Path $rootDir "build\pyinstaller") `
    (Join-Path $rootDir "python\desktop_app.py")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller konnte RefCalendar nicht paketieren."
}

Copy-Item -LiteralPath $oauthConfig -Destination (Join-Path $distributionDir "credentials.json") -Force

$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $compiler) {
    $knownCompilerPaths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $knownCompilerPath = $knownCompilerPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($knownCompilerPath) {
        $compilerPath = $knownCompilerPath
    } else {
        throw "Inno Setup 6 wurde nicht gefunden. Installiere Inno Setup 6 oder füge ISCC.exe zum PATH hinzu."
    }
} else {
    $compilerPath = $compiler.Source
}

& $compilerPath (Join-Path $rootDir "installer.iss")
if ($LASTEXITCODE -ne 0) {
    throw "Der RefCalendar-Installer konnte nicht erstellt werden."
}

Write-Host "Installer erstellt: dist\installer\RefCalendar-Setup-0.1.0.exe"
