"""Key handling for the vault (envelope encryption).

Every entry is encrypted with a random Fernet *data key*. The data key is never
stored in plaintext. It is wrapped (Fernet-encrypted) with a *key-encryption key*
derived from the master password using scrypt. Without the master password the
database contents can't be decrypted, and changing the master password only
means re-wrapping one key.

A *recovery key* wraps the same data key a second time, so a forgotten master
password can be replaced. It is 25 random characters (125 bits), far too many to
guess, so a fast HKDF is enough to turn it into a key-encryption key.
"""

from __future__ import annotations

import base64
import os
import secrets
import unicodedata
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

__all__ = [
    "InvalidToken", "KdfParams", "derive_kek", "derive_recovery_kek", "format_recovery_key",
    "new_kdf_params", "new_recovery_key", "normalize_recovery_key", "unwrap_key", "wrap_key",
]

# scrypt cost: 2**17 * 8 * 128 bytes = 128 MiB of memory, about 0.3-1 s per guess on a desktop.
DEFAULT_N = 2**17
DEFAULT_R = 8
DEFAULT_P = 1
SALT_BYTES = 16

# Crockford base32: no I, L, O or U, so the key can't be misread when written down.
RECOVERY_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
RECOVERY_LENGTH = 25  # 25 x 5 bits = 125 bits
RECOVERY_GROUP = 5
_RECOVERY_LOOKALIKES = str.maketrans({"O": "0", "I": "1", "L": "1"})


@dataclass(frozen=True)
class KdfParams:
    salt: bytes
    n: int = DEFAULT_N
    r: int = DEFAULT_R
    p: int = DEFAULT_P

    @property
    def salt_b64(self) -> str:
        return base64.b64encode(self.salt).decode("ascii")

    @classmethod
    def from_db(cls, salt_b64: str, n: int, r: int, p: int) -> "KdfParams":
        return cls(salt=base64.b64decode(salt_b64), n=int(n), r=int(r), p=int(p))


def new_kdf_params() -> KdfParams:
    return KdfParams(salt=os.urandom(SALT_BYTES))


def _normalize(master_password: str) -> bytes:
    # NFC, so the same password typed on different OSes and keyboards derives the same key.
    return unicodedata.normalize("NFC", master_password).encode("utf-8")


def derive_kek(master_password: str, params: KdfParams) -> Fernet:
    raw = Scrypt(salt=params.salt, length=32, n=params.n, r=params.r, p=params.p).derive(
        _normalize(master_password)
    )
    return Fernet(base64.urlsafe_b64encode(raw))


def wrap_key(data_key: bytes, kek: Fernet) -> str:
    return kek.encrypt(data_key).decode("ascii")


def unwrap_key(wrapped: str, kek: Fernet) -> bytes:
    """Return the data key. Raises InvalidToken if the master password is wrong."""
    return kek.decrypt(wrapped.encode("ascii"))


def new_recovery_key() -> str:
    """A new recovery key, formatted for display, e.g. ``7KQ4M-ZP2XW-...``."""
    return format_recovery_key("".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_LENGTH)))


def format_recovery_key(key: str) -> str:
    key = normalize_recovery_key(key)
    return "-".join(key[i:i + RECOVERY_GROUP] for i in range(0, RECOVERY_LENGTH, RECOVERY_GROUP))


def normalize_recovery_key(text: str) -> str:
    """Upper-case it, drop spaces and dashes, and fix look-alike letters. Raises ValueError
    if the result can't be a recovery key (so a typo there doesn't count as a failed attempt)."""
    key = "".join(text.split()).replace("-", "").upper().translate(_RECOVERY_LOOKALIKES)
    if len(key) != RECOVERY_LENGTH or any(c not in RECOVERY_ALPHABET for c in key):
        raise ValueError(f"A recovery key is {RECOVERY_LENGTH} letters and digits, like the one you saved.")
    return key


def derive_recovery_kek(recovery_key: str, salt: bytes) -> Fernet:
    raw = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"password-manager recovery key v1").derive(
        normalize_recovery_key(recovery_key).encode("ascii")
    )
    return Fernet(base64.urlsafe_b64encode(raw))
