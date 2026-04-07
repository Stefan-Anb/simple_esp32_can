# Prüfen, ob ein Parameter übergeben wurde, sonst Standard COM19
if ($args.Count -gt 0) {
    $Port = $args[0]
} else {
    $Port = "COM19"
}

Write-Host "Verwende Port: $Port"

$ErrorActionPreference = "Stop"

$pythonVersion = "3.14.3"
$toolDir = "$PSScriptRoot\.tool"
$pythonDir = "$toolDir\python"
$pythonExe = "$pythonDir\python.exe"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

# Python embedded herunterladen
if (!(Test-Path $pythonDir)) {
    Write-Host "Downloading Python $pythonVersion..."
    $url = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
    $zip = "$toolDir\python.zip"
    
    New-Item -ItemType Directory -Force -Path $toolDir | Out-Null
    Invoke-WebRequest -Uri $url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $pythonDir -Force
    Remove-Item $zip
    
    # import site aktivieren
    $pthFile = Get-ChildItem "$pythonDir\*._pth" | Select-Object -First 1
    (Get-Content $pthFile) -replace '#import site', 'import site' | Set-Content $pthFile
}

# get-pip installieren
if (!(Test-Path "$pythonDir\Lib\site-packages\pip")) {
    Write-Host "Installing pip..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "$toolDir\get-pip.py"
    Invoke-Checked -Description "pip bootstrap" -Command { & $pythonExe "$toolDir\get-pip.py" }
    Remove-Item "$toolDir\get-pip.py"
}

if (!(Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe"
}

# setuptools vorbereiten
Invoke-Checked -Description "pip upgrade" -Command { & $pythonExe -m pip install --upgrade pip setuptools wheel }

# Dependencies direkt installieren (kein venv bei embedded)
Write-Host "Installing dependencies..."
Invoke-Checked -Description "dependency installation" -Command { & $pythonExe -m pip install -r "$PSScriptRoot\requirements.txt" --no-warn-script-location }

cd package

python -m esptool --chip esp32s3 -b 460800 --before default_reset --after hard_reset --port $Port write_flash --flash_mode dio --flash_size 4MB --flash_freq 80m 0x0 bootloader.bin 0x10000 simple_esp32_can.bin 0x8000 partition-table.bin 0xd000 ota_data_initial.bin

Write-Host "`nSetup complete!"

cd ..