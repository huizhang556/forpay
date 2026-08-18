import base64
import hashlib
import json
from urllib.parse import urlparse

import httpx
from app import __version__
from app.core.config import get_settings
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class UpdateError(ValueError):
    pass


def _https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise UpdateError("update URLs must use HTTPS")
    if parsed.hostname.lower() in {"localhost", "metadata.google.internal"}:
        raise UpdateError("update URL host is not allowed")
    return value


async def check_update() -> dict:
    settings = get_settings()
    if not settings.update_manifest_url or not settings.update_public_key:
        raise UpdateError("signed update checking is not configured")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(settings.update_public_key))
    except Exception as exc:
        raise UpdateError("invalid update public key") from exc
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.get(_https_url(settings.update_manifest_url), headers={"Accept": "application/json"})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise UpdateError("update manifest is temporarily unavailable") from exc
    if len(response.content) > 64 * 1024:
        raise UpdateError("update manifest is too large")
    try:
        manifest = response.json()
        signature = base64.b64decode(manifest.pop("signature"))
        canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        public_key.verify(signature, canonical)
    except (KeyError, ValueError, TypeError, InvalidSignature) as exc:
        raise UpdateError("update manifest signature verification failed") from exc
    if not isinstance(manifest.get("version"), str) or not isinstance(manifest.get("sha256"), str):
        raise UpdateError("update manifest is missing required fields")
    package_url = _https_url(str(manifest.get("url", "")))
    digest = manifest["sha256"].lower()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise UpdateError("invalid update package digest")
    return {"current_version": __version__, "available_version": manifest["version"], "update_available": manifest["version"] != __version__, "url": package_url, "sha256": digest, "notes": manifest.get("notes", "")}


def verify_package_digest(content: bytes, expected_sha256: str) -> bool:
    return hashlib.sha256(content).hexdigest() == expected_sha256.lower()
