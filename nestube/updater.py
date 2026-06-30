"""
nestube/nestube/nestube/updater.py
Check GitHub Releases for a newer NesTube version and optional installer download.
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import __version__

GITHUB_REPO = "Grohle/nestube"
RELEASES_LATEST_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"NesTube/{__version__}"

# Hosts GitHub uses for the releases API and for serving release assets. A
# browser_download_url on github.com 302-redirects to one of the
# *.githubusercontent.com CDN hosts, so those must be trusted for redirects too.
_TRUSTED_HOSTS = frozenset({
    "github.com",
    "api.github.com",
    "codeload.github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
})


class UntrustedURLError(Exception):
    """A URL is not HTTPS to a GitHub-controlled host and was refused."""


class HashMismatchError(Exception):
    """Downloaded file SHA-256 does not match the expected value."""


def _host_is_trusted(host: str) -> bool:
    host = (host or "").lower()
    return host in _TRUSTED_HOSTS or host.endswith(".githubusercontent.com")


def _require_trusted_url(url: str) -> str:
    """Reject any URL that is not HTTPS to a GitHub-controlled host.

    The installer and checksum URLs come from the GitHub API response — data we
    do not fully control. Without this guard a tampered or unexpected response
    could point fetch_sha256()/download_file() at file://, http:// or an
    arbitrary host, and urllib would happily read/download it.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not _host_is_trusted(parts.hostname or ""):
        raise UntrustedURLError(f"Refusing to fetch untrusted URL: {url!r}")
    return url


class _TrustedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect target so an HTTPS→HTTP or off-host
    downgrade in a redirect chain cannot bypass _require_trusted_url()."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _require_trusted_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url: str, *, timeout: float, accept: Optional[str] = None):
    """Open a trusted GitHub URL through an opener that validates redirects."""
    _require_trusted_url(url)
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(
        _TrustedRedirectHandler, urllib.request.HTTPSHandler(context=ctx)
    )
    return opener.open(request, timeout=timeout)


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    tag_name: str
    release_name: str
    release_notes: str
    html_url: str
    installer_url: Optional[str]
    installer_name: Optional[str]
    installer_sha256_url: Optional[str] = field(default=None)

    @property
    def update_available(self) -> bool:
        return version_tuple(self.latest_version) > version_tuple(self.current_version)


def version_tuple(version: str) -> Tuple[int, ...]:
    """Parse '1.0.0' or 'v1.0.0' into comparable tuple."""
    cleaned = version.strip().lstrip("vV")
    parts: List[int] = []
    for piece in cleaned.split("."):
        m = re.match(r"(\d+)", piece)
        if m:
            parts.append(int(m.group(1)))
        else:
            break
    return tuple(parts) if parts else (0,)


def _installer_asset(release: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (installer_url, installer_name, sha256_url)."""
    inst_url: Optional[str] = None
    inst_name: Optional[str] = None
    # Map lowercase base name → download URL for .sha256 companion assets
    sha256_map: dict[str, str] = {}

    for asset in release.get("assets") or []:
        name = str(asset.get("name", ""))
        lower = name.lower()
        if lower.endswith("-setup.exe") or lower.endswith("_setup.exe") or lower.endswith(" setup.exe"):
            inst_url = asset.get("browser_download_url")
            inst_name = name
        elif lower.endswith(".sha256.txt"):
            base = name[: -len(".sha256.txt")]
            sha256_map[base.lower()] = str(asset.get("browser_download_url") or "")
        elif lower.endswith(".sha256"):
            base = name[: -len(".sha256")]
            sha256_map[base.lower()] = str(asset.get("browser_download_url") or "")

    sha256_url = sha256_map.get(inst_name.lower()) if inst_name else None
    return inst_url, inst_name, sha256_url


def check_for_update(timeout: float = 12.0) -> Optional[UpdateInfo]:
    """
    Query GitHub for the latest release. Returns None if offline or API error.
    """
    try:
        with _open(RELEASES_LATEST_URL, timeout=timeout,
                   accept="application/vnd.github+json") as resp:
            release = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            TimeoutError, UntrustedURLError):
        return None

    tag = str(release.get("tag_name", "")).strip() or str(release.get("name", "")).strip()
    latest = tag.lstrip("vV") if tag else __version__
    inst_url, inst_name, sha256_url = _installer_asset(release)
    notes = str(release.get("body") or "").strip()
    if len(notes) > 1200:
        notes = notes[:1197] + "..."

    return UpdateInfo(
        current_version=__version__,
        latest_version=latest,
        tag_name=tag or f"v{latest}",
        release_name=str(release.get("name") or tag or latest),
        release_notes=notes,
        html_url=str(release.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases/latest"),
        installer_url=inst_url,
        installer_name=inst_name,
        installer_sha256_url=sha256_url,
    )


def fetch_sha256(url: str, timeout: float = 30.0) -> str:
    """Download a .sha256 asset and return the hex digest (lowercase, no filename)."""
    with _open(url, timeout=timeout) as resp:
        content = resp.read().decode("utf-8", errors="replace").strip()
    # Accepts "<hex>" or "<hex>  <filename>" (sha256sum / CertUtil format)
    return content.split()[0].lower()


def verify_sha256(file_path: str, expected_hex: str) -> None:
    """Raise HashMismatchError if the SHA-256 of file_path != expected_hex."""
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    actual = h.hexdigest().lower()
    if actual != expected_hex.strip().lower():
        raise HashMismatchError(
            f"SHA-256 mismatch\n  expected: {expected_hex.strip().lower()}\n  got:      {actual}"
        )


def download_file(url: str, dest_path: str, timeout: float = 120.0) -> None:
    """Download a release asset to dest_path."""
    with _open(url, timeout=timeout) as resp:
        data = resp.read()
    with open(dest_path, "wb") as fh:
        fh.write(data)
