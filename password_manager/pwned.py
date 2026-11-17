"""Check passwords against Have I Been Pwned's list of leaked passwords without revealing them.

Only the first five characters of each password's SHA-1 hash leave this computer (k-anonymity):
the service returns every leaked hash that starts with them, and the match happens here.
"""

from __future__ import annotations

import hashlib
import ssl
import urllib.request
from collections import defaultdict
from typing import Callable, Dict, Iterable

API = "https://api.pwnedpasswords.com/range/"


def tls_context() -> ssl.SSLContext:
    """Verify HTTPS against the certificate list that ships with the app (certifi). A built app
    (PyInstaller) can't see the certificate file of the Python it was built from."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return ssl.create_default_context()


def _fetch(prefix: str, timeout: float = 15) -> str:
    request = urllib.request.Request(API + prefix, headers={"User-Agent": "password-manager-breach-check",
                                                            "Add-Padding": "true"})
    with urllib.request.urlopen(request, timeout=timeout, context=tls_context()) as response:
        return response.read().decode("utf-8")


def check(passwords: Iterable[str], fetch: Callable[[str], str] = _fetch) -> Dict[str, int]:
    """{password: how many times it appears in known breaches (0 = not found)}."""
    by_prefix = defaultdict(list)
    for password in set(p for p in passwords if p):
        digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        by_prefix[digest[:5]].append((password, digest[5:]))
    result: Dict[str, int] = {}
    for prefix, items in by_prefix.items():
        counts = {}
        for line in fetch(prefix).splitlines():
            suffix, _, count = line.partition(":")
            if suffix.strip():
                counts[suffix.strip().upper()] = int(count.strip() or 0)
        for password, suffix in items:
            result[password] = counts.get(suffix, 0)
    return result
