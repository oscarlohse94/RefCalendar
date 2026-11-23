$ErrorActionPreference = "Stop"

if ($MyInvocation.InvocationName -ne ".") {
    Write-Error 'Das Skript muss in der aktuellen PowerShell mit ". .\setup.ps1" gestartet werden.'
    exit 1
}

$rootDir = $PSScriptRoot
$envFile = Join-Path $rootDir ".env"
$venvDir = Join-Path $rootDir ".venv"

$pythonCommand = $null
$pythonArguments = @()

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" *> $null
    if ($LASTEXITCODE -eq 0) {
        $pythonCommand = "py"
        $pythonArguments = @("-3")
    }
}

if ($null -eq $pythonCommand) {
    foreach ($candidate in @("python", "python3")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch '[\\/]Microsoft[\\/]WindowsApps[\\/]') {
            & $candidate -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" *> $null
            if ($LASTEXITCODE -eq 0) {
                $pythonCommand = $candidate
                break
            }
        }
    }
}

if ($null -eq $pythonCommand) {
    throw "Python 3.10 oder neuer wurde nicht gefunden (die Microsoft-Store-Aliasse zaehlen nicht). Installiere Python von https://www.python.org/downloads/ und waehle im Installer ``Add python.exe to PATH`` sowie ``pip``."
}

$pythonArgsPrefix = $pythonArguments
& $pythonCommand @pythonArgsPrefix -c "import pip" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "System-Python benoetigt pip. Installiere Python erneut und waehle die Option ``pip``."
}

& $pythonCommand @pythonArgsPrefix -m pip --help *> $null
if ($LASTEXITCODE -ne 0) {
    throw "pip konnte nicht ausgefuehrt werden."
}
$pipHelp = & $pythonCommand @pythonArgsPrefix -m pip --help
$pipHelpText = $pipHelp -join [Environment]::NewLine
if ($pipHelpText -notmatch "(?m)\s--python") {
    throw "Die installierte pip-Version unterstuetzt die Option --python nicht. Aktualisiere pip mit ``py -3 -m pip install --upgrade pip``."
}

if (Test-Path $envFile) {
    $prompt = "DHB-URL eingeben, CLIPBOARD fuer Zwischenablage oder Enter zum Beibehalten (Eingabe wird angezeigt):"
} else {
    $prompt = "DHB-URL eingeben oder CLIPBOARD fuer Zwischenablage (Eingabe wird angezeigt):"
}
$dhbUrl = Read-Host $prompt
if ($dhbUrl -eq "CLIPBOARD") {
    $dhbUrl = (Get-Clipboard -Raw | Out-String).Trim()
}

if (-not [string]::IsNullOrWhiteSpace($dhbUrl)) {
    if ($dhbUrl -notmatch '^https://dhb\.refsoft\.de/api/index\.php\?m=.+$') {
        $dhbUrl = $null
        throw "Die URL hat nicht das erwartete DHB-Format. Die .env-Datei blieb unveraendert."
    }

    $existingLines = if (Test-Path $envFile) {
        [System.IO.File]::ReadAllLines($envFile)
    } else {
        @()
    }

    $replaced = $false
    $updatedLines = foreach ($line in $existingLines) {
        if ($line -match '^\s*(?:export\s+)?DHB_URL\s*=') {
            if (-not $replaced) {
                "DHB_URL=$dhbUrl"
                $replaced = $true
            }
        } else {
            $line
        }
    }
    if (-not $replaced) {
        $updatedLines += "DHB_URL=$dhbUrl"
    }

    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($envFile, [string[]]$updatedLines, $utf8WithoutBom)
    $dhbUrl = $null
    Write-Host "DHB-URL in .env aktualisiert."
} elseif (Test-Path $envFile) {
    Write-Host "Bisherige DHB-URL bleibt unveraendert."
} else {
    $dhbUrl = $null
    throw "Ohne eine DHB-URL kann keine .env-Datei erstellt werden."
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    if (Test-Path $venvDir) {
        throw ".venv existiert, enthalt aber keinen funktionsfaehigen Python-Interpreter. Bitte pruefe sie manuell."
    }
    & $pythonCommand @pythonArgsPrefix -m venv --without-pip $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw ".venv konnte nicht erstellt werden."
    }
    Write-Host ".venv wurde erstellt."
} else {
    Write-Host "Vorhandene .venv wird weiterverwendet."
}

& $pythonCommand @pythonArgsPrefix -m pip --python $venvPython install --editable $rootDir
if ($LASTEXITCODE -ne 0) {
    throw "RefCalendar konnte nicht in .venv installiert werden."
}

$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    throw ".venv wurde installiert, enthalt aber kein Aktivierungsskript."
}
. $activateScript

Write-Host ".venv ist jetzt in dieser PowerShell aktiviert. Zum Verlassen ``deactivate`` ausfuehren."
