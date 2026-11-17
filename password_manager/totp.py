"""Time-based one-time passwords (RFC 6238): the 6-digit codes sites ask for at sign-in."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import struct
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

ALGORITHMS = {"SHA1": hashlib.sha1, "SHA256": hashlib.sha256, "SHA512": hashlib.sha512}


@dataclass(frozen=True)
class Totp:
    secret: bytes
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"
    issuer: str = ""
    account: str = ""

    def code(self, at: Optional[float] = None) -> str:
        counter = int((time.time() if at is None else at) // self.period)
        mac = hmac.new(self.secret, struct.pack(">Q", counter), ALGORITHMS[self.algorithm]).digest()
        offset = mac[-1] & 0x0F
        value = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(value % 10 ** self.digits).zfill(self.digits)

    def remaining(self, at: Optional[float] = None) -> int:
        return self.period - int(time.time() if at is None else at) % self.period


def _secret(text: str) -> bytes:
    cleaned = "".join(text.split()).replace("-", "").upper().rstrip("=")
    if not cleaned:
        raise ValueError("Enter the 2FA secret key or the otpauth:// link.")
    try:
        key = base64.b32decode(cleaned + "=" * (-len(cleaned) % 8))
    except (binascii.Error, ValueError):
        raise ValueError("That isn't a valid 2FA secret key. It's usually 16 or 32 letters and digits.") from None
    if len(key) < 10:
        raise ValueError("That 2FA secret key is too short.")
    return key


def parse(text: str) -> Totp:
    """A base32 secret ("JBSW Y3DP ...") or an otpauth://totp/... link from a QR code."""
    text = text.strip()
    if not text.lower().startswith("otpauth://"):
        return Totp(_secret(text))
    url = urlparse(text)
    if url.netloc.lower() != "totp":
        raise ValueError("Only time-based (TOTP) codes are supported.")
    query = {k.lower(): v[0] for k, v in parse_qs(url.query).items()}
    label = unquote(url.path.lstrip("/"))
    issuer = query.get("issuer", "") or (label.split(":", 1)[0] if ":" in label else "")
    algorithm = query.get("algorithm", "SHA1").upper()
    try:
        digits, period = int(query.get("digits", 6)), int(query.get("period", 30))
    except ValueError:
        raise ValueError("That otpauth link has invalid settings.") from None
    if algorithm not in ALGORITHMS or digits not in (6, 7, 8) or not 10 <= period <= 300:
        raise ValueError("That otpauth link uses settings this app doesn't support.")
    return Totp(_secret(query.get("secret", "")), digits, period, algorithm, issuer, label.split(":", 1)[-1])


def is_valid(text: str) -> bool:
    try:
        parse(text)
        return True
    except ValueError:
        return False
