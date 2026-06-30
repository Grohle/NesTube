# Build portable Nestify for Windows (run from repo root in PowerShell)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent) | Out-Null

python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt
pyinstaller --noconfirm packaging/nestify.spec

$ver = python -c "from nestify import __version__; print(__version__)"
$zip = "Nestify-$ver-windows.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "dist\Nestify" -DestinationPath $zip
Write-Host "Built: dist\Nestify\Nestify.exe"
Write-Host "Archive: $zip"
