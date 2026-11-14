"""Key handling for the vault (envelope encryption).

Every entry is encrypted with a random Fernet *data key*. The data key is never
stored in plaintext. It is wrapped (Fernet-encrypted) with a *key-encryption key*
derived from the master password using scrypt. Without the master password the
database contents can't be decrypted, and changing the master password only
means re-wrapping one key.
"""

from __future__ import annotations

import base64
import os
import unicodedata
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

__all__ = ["InvalidToken", "KdfParams", "derive_kek", "new_kdf_params", "unwrap_key", "wrap_key"]

# scrypt cost: 2**17 * 8 * 128 bytes = 128 MiB of memory, about 0.3-1 s per guess on a desktop.
DEFAULT_N = 2**17
DEFAULT_R = 8
DEFAULT_P = 1
SALT_BYTES = 16


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
