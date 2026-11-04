"""Cryptographic key security, AES-256-GCM encryption at rest, log scrubbing, and SSRF guard."""

import base64
import hashlib
import ipaddress
import os
import re
import socket
from urllib.parse import urlparse

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings
from app.core.errors import SecurityViolationError

# Global pattern for matching common API keys and tokens in text/logs
_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}"),
    re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"),
    re.compile(r"gsk_[a-zA-Z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"hf_[a-zA-Z0-9]{20,}"),
    re.compile(r"xai-[a-zA-Z0-9_-]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]{20,}", re.IGNORECASE),
]

_DEV_AUTO_KEY_FILE = "dev_encryption_secret.key"


def _derive_master_key() -> bytes:
    """Retrieve master encryption secret from settings or auto-generate for dev mode."""
    settings = get_settings()
    secret = settings.key_encryption_secret

    if not secret:
        if settings.app_env == "production":
            raise SecurityViolationError(
                "KEY_ENCRYPTION_SECRET must be explicitly set and at least 32 characters in production."
            )
        # Development fallback: persist an untracked local key file
        data_dir = settings.data_dir
        os.makedirs(data_dir, exist_ok=True)
        key_path = os.path.join(data_dir, _DEV_AUTO_KEY_FILE)
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        generated = os.urandom(32)
        with open(key_path, "wb") as f:
            f.write(generated)
        return generated

    # Derive 32-byte key via SHA-256 from provided secret string
    return hashlib.sha256(secret.encode("utf-8")).digest()


def encrypt_api_key(plaintext_key: str, key_version: str = "v1") -> str:
    """Encrypt a user-provided LLM API key with AES-256-GCM.

    Returns formatted ciphertext: '<version>:<base64_nonce_and_ciphertext>'
    """
    if not plaintext_key or not plaintext_key.strip():
        raise ValueError("Plaintext API key cannot be empty")

    master_key = _derive_master_key()
    aesgcm = AESGCM(master_key)
    nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
    data = plaintext_key.strip().encode("utf-8")
    ct = aesgcm.encrypt(nonce, data, None)

    combined = nonce + ct
    encoded = base64.b64encode(combined).decode("ascii")
    return f"{key_version}:{encoded}"


def decrypt_api_key(encrypted_str: str) -> str:
    """Decrypt an AES-256-GCM encrypted API key.

    Authenticates integrity tag and handles key versions.
    """
    if not encrypted_str or ":" not in encrypted_str:
        raise ValueError("Invalid encrypted key format")

    parts = encrypted_str.split(":", 1)
    # version = parts[0]  # for future key rotation
    combined = base64.b64decode(parts[1].encode("ascii"))

    if len(combined) < 28:  # 12 bytes nonce + 16 bytes auth tag minimum
        raise ValueError("Ciphertext too short")

    nonce = combined[:12]
    ciphertext = combined[12:]

    master_key = _derive_master_key()
    aesgcm = AESGCM(master_key)
    try:
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag as e:
        raise SecurityViolationError(
            "Decryption failed: integrity authentication tag mismatch or corrupted ciphertext."
        ) from e
    return plaintext_bytes.decode("utf-8")


def mask_key_hint(key: str) -> str:
    """Return a masked representation exposing only the last 4 characters."""
    clean = key.strip()
    if len(clean) <= 4:
        return "..." + clean
    return f"...{clean[-4:]}"


def scrub_secrets_from_text(text: str) -> str:
    """Scrub common credential patterns and bearer tokens from logs and error strings."""
    scrubbed = text
    for pattern in _SECRET_PATTERNS:
        scrubbed = pattern.sub("[REDACTED_CREDENTIAL]", scrubbed)
    return scrubbed


def validate_outbound_url_ssrf(url: str, allow_dev_localhost: bool = True) -> str:
    """Validate that an outbound base URL or endpoint does not target internal network ranges.

    Blocks 10/8, 172.16/12, 192.168/16, 127/8, 169.254/16 (AWS metadata), IPv6 link-local, etc.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname

    if not hostname:
        raise SecurityViolationError("Invalid URL: missing hostname")

    settings = get_settings()
    is_dev = settings.app_env == "development"

    if scheme != "https":
        if is_dev and allow_dev_localhost and hostname in ("localhost", "127.0.0.1", "::1"):
            pass  # Allowed for local Ollama / vLLM during local development
        else:
            raise SecurityViolationError(f"Protocol '{scheme}' disallowed; outbound URLs must use HTTPS.")

    # Resolve IP addresses
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SecurityViolationError(f"DNS resolution failed for host '{hostname}': {e}") from e

    for _family, _, _, _, sockaddr in addr_infos:
        ip_str = str(sockaddr[0])
        ip = ipaddress.ip_address(ip_str)

        # Allow local loopback if dev localhost
        if is_dev and allow_dev_localhost and ip.is_loopback:
            continue

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or (ip.version == 4 and ip_str.startswith("169.254."))  # Cloud metadata service
        ):
            raise SecurityViolationError(
                f"Outbound request to internal or restricted IP range {ip_str} is prohibited."
            )

    return url
