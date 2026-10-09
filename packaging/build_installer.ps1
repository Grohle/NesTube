# Build NesTube Windows installer (PyInstaller + Inno Setup 6)
# Run from repository root in PowerShell on Windows.
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "==> Installing Python dependencies"
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt

Write-Host "==> Building application bundle (PyInstaller)"
python -m PyInstaller --noconfirm packaging/nestube.spec
if (-not (Test-Path "dist\NesTube\NesTube.exe")) {
    throw "dist\NesTube\NesTube.exe not found after PyInstaller build"
}

$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
    $Iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
}
if (-not (Test-Path $Iscc)) {
    throw "Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php"
}

$ver = python -c "from nestube import __version__; print(__version__)"

# Sign the app before packaging (no-op with a warning when no certificate is
# set in WINDOWS_CERT_PFX_BASE64 / WINDOWS_CERT_PASSWORD; see docs/signing.md).
& "$PSScriptRoot\sign_windows.ps1" "dist\NesTube\NesTube.exe"

Write-Host "==> Building installer (Inno Setup) for version $ver"
& $Iscc "/DMyAppVersion=$ver" "packaging\nestube.iss"

$setup = "NesTube-$ver-setup.exe"
if (Test-Path $setup) {
    & "$PSScriptRoot\sign_windows.ps1" $setup
    Write-Host "OK: $setup"
} else {
    Get-ChildItem -Filter "NesTube-*-setup.exe" | ForEach-Object { Write-Host "OK: $($_.Name)" }
}
