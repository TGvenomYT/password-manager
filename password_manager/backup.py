"""Encrypted backups (.pmbackup): every entry, sealed with a backup password you choose.

The file is JSON: scrypt settings plus one Fernet token, the same protection as the vault itself,
so it's safe to keep on a USB stick or in cloud storage.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Iterable, List

from cryptography.fernet import InvalidToken

from . import crypto

FORMAT = "password-manager-backup"
VERSION = 1
MIN_LENGTH = 8


def entry_dict(entry) -> dict:
    return {"title": entry.title, "username": entry.username, "password": entry.password or "",
            "website": entry.website, "notes": entry.notes, "totp": entry.totp, "kind": entry.kind,
            "favorite": entry.favorite, "history": list(entry.history)}


def write(path, entries: Iterable, password: str,
          kdf_params: Callable[[], crypto.KdfParams] = crypto.new_kdf_params) -> int:
    if len(password) < MIN_LENGTH:
        raise ValueError(f"The backup password must be at least {MIN_LENGTH} characters.")
    items = [entry_dict(e) for e in entries if e.password is not None]
    params = kdf_params()
    payload = json.dumps({"created": time.time(), "entries": items}, ensure_ascii=False).encode("utf-8")
    document = {"format": FORMAT, "version": VERSION, "kdf": "scrypt", "salt": params.salt_b64,
                "n": params.n, "r": params.r, "p": params.p,
                "data": crypto.derive_kek(password, params).encrypt(payload).decode("ascii")}
    Path(path).write_text(json.dumps(document, indent=2), encoding="utf-8")
    return len(items)


def read(path, password: str) -> List[dict]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"Couldn't read the backup file: {exc}") from None
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise ValueError("That file isn't a Password Manager backup.")
    if document.get("version", 0) > VERSION:
        raise ValueError("That backup was made by a newer version of the app.")
    params = crypto.KdfParams.from_db(document["salt"], document["n"], document["r"], document["p"])
    try:
        payload = crypto.derive_kek(password, params).decrypt(document["data"].encode("ascii"))
    except InvalidToken:
        raise ValueError("Wrong backup password.") from None
    return json.loads(payload.decode("utf-8"))["entries"]
