# Build portable NesTube for Windows (run from repo root in PowerShell)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent) | Out-Null

python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt
pyinstaller --noconfirm packaging/nestube.spec

$ver = python -c "from nestube import __version__; print(__version__)"
$zip = "NesTube-$ver-windows.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "dist\NesTube" -DestinationPath $zip
Write-Host "Built: dist\NesTube\NesTube.exe"
Write-Host "Archive: $zip"
