# Signing the Windows build

Unsigned Windows programs trigger SmartScreen ("Windows protected your PC")
on first launch. The release workflow signs `NesTube.exe` and the installer
with Authenticode **when a code-signing certificate is configured**; without
one it builds exactly as before and prints a warning.

## 1. Get a certificate

| Option | Cost | Notes |
|---|---|---|
| [SignPath Foundation](https://signpath.org/) | Free for open-source projects | Apply with the repository; they sign through their own GitHub Action (a different step from the one below). |
| [Azure Trusted Signing](https://learn.microsoft.com/azure/trusted-signing/) | About 10 US$/month | Identity validation by Microsoft; uses the `azure/trusted-signing-action` step. |
| OV code-signing certificate (Sectigo, DigiCert, SSL.com, Certum…) | About 100–400 €/year | Exported as a `.pfx` file: works with the step already in the workflow. |

Since 2023, new OV/EV certificates are usually issued on a hardware token or
a cloud HSM, not as a `.pfx` file. Check that the provider offers a `.pfx` or
cloud-signing option before buying. Certum's open-source certificate and
SignPath are the cheapest routes for a free project.

SmartScreen reputation also builds up with downloads. A new certificate may
still show the warning for the first releases.

## 2. Add it to the repository (`.pfx` route)

In **GitHub → Settings → Secrets and variables → Actions → New repository
secret**, add:

| Secret | Value |
|---|---|
| `WINDOWS_CERT_PFX_BASE64` | The `.pfx` file in base64. PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.pfx")) \| Set-Clipboard` |
| `WINDOWS_CERT_PASSWORD` | The `.pfx` password |

The next release run signs `dist\NesTube\NesTube.exe` before zipping and
`NesTube-<version>-setup.exe` after Inno Setup, timestamps both (DigiCert's
RFC 3161 server) and verifies the signatures (`packaging/sign_windows.ps1`).

## 3. Local builds

`packaging\build_installer.ps1` calls the same script. Set the two variables
in the shell first to sign locally:

```powershell
$env:WINDOWS_CERT_PFX_BASE64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.pfx"))
$env:WINDOWS_CERT_PASSWORD = "…"
.\packaging\build_installer.ps1
```
