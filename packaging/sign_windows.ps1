# Sign Windows executables with Authenticode (signtool), if a certificate is set.
#
#   .\packaging\sign_windows.ps1 dist\NesTube\NesTube.exe NesTube-0.1.0-setup.exe
#
# The certificate comes from the environment (GitHub secrets in CI):
#   WINDOWS_CERT_PFX_BASE64   the .pfx file, base64-encoded
#   WINDOWS_CERT_PASSWORD     its password
#   WINDOWS_SIGN_TIMESTAMP    optional RFC 3161 timestamp server
#                             (default http://timestamp.digicert.com)
# Without a certificate the files are left unsigned and a warning is printed,
# so builds keep working; SmartScreen then warns on first launch.
# See docs/signing.md.
param([Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)][string[]]$Files)
$ErrorActionPreference = "Stop"

if (-not $env:WINDOWS_CERT_PFX_BASE64) {
    Write-Host "::warning::No code-signing certificate configured (WINDOWS_CERT_PFX_BASE64); leaving $($Files -join ', ') unsigned."
    exit 0
}

$signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName | Select-Object -Last 1
if (-not $signtool) { throw "signtool.exe not found (install the Windows 10/11 SDK)" }

$timestamp = if ($env:WINDOWS_SIGN_TIMESTAMP) { $env:WINDOWS_SIGN_TIMESTAMP } else { "http://timestamp.digicert.com" }
$pfx = Join-Path ([System.IO.Path]::GetTempPath()) ("nestube-sign-" + [guid]::NewGuid() + ".pfx")
try {
    [System.IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:WINDOWS_CERT_PFX_BASE64))
    foreach ($f in $Files) {
        if (-not (Test-Path $f)) { throw "File to sign not found: $f" }
        Write-Host "==> Signing $f"
        & $signtool.FullName sign /fd sha256 /tr $timestamp /td sha256 /f $pfx /p $env:WINDOWS_CERT_PASSWORD /d "NesTube" $f
        if ($LASTEXITCODE -ne 0) { throw "signtool failed on $f" }
        & $signtool.FullName verify /pa $f
        if ($LASTEXITCODE -ne 0) { throw "signature does not verify on $f" }
    }
} finally {
    Remove-Item $pfx -Force -ErrorAction SilentlyContinue
}
