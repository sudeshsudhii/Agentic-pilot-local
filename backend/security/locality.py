"""Keep model inference and vector-store traffic on the user's machine.

A model endpoint counts as local only if its host is a loopback name or address.
LAN addresses are not local: a prompt sent to another machine has left this one.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

LOOPBACK_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}


class NonLocalEndpointError(ValueError):
    """Raised when a model endpoint is not on this machine and remote use is not allowed."""


def is_loopback_url(url: str) -> bool:
    """Return True if the URL's host is a loopback name or a loopback IP address."""

    try:
        host = urlsplit(url if "://" in url else f"http://{url}").hostname
    except ValueError:
        return False
    if not host:
        return False
    host = host.lower().rstrip(".")
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_local_endpoint(url: str, allow_remote: bool) -> None:
    """Refuse a non-loopback model endpoint unless the user explicitly allowed it."""

    if allow_remote or is_loopback_url(url):
        return
    raise NonLocalEndpointError(
        f"Model endpoint {url!r} is not on this machine. Prompts and screenshots would leave it. "
        "Set PILOT_ALLOW_REMOTE_MODEL=true to allow this deliberately."
    )


def local_chroma_settings():
    """Chroma settings with product telemetry disabled."""

    from chromadb.config import Settings

    return Settings(anonymized_telemetry=False)
