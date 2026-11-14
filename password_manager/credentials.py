"""The MySQL password, stored GPG-encrypted (symmetric AES-256) on disk.

The passphrase is passed to gpg on stdin in loopback pinentry mode, so the app
works the same whether it was launched from a terminal, a .app bundle, a
desktop entry, or a Windows shortcut. Nothing depends on which pinentry program
is installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

MAX_PASSPHRASE_ATTEMPTS = 3


class GpgError(Exception):
    pass


class GpgNotFound(GpgError):
    pass


class BadPassphrase(GpgError):
    pass


class PassphraseCancelled(GpgError):
    pass


def _candidates():
    if sys.platform == "win32":
        for var in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            base = os.environ.get(var)
            if base:
                yield Path(base) / "GnuPG" / "bin" / "gpg.exe"
                yield Path(base) / "Gpg4win" / ".." / "GnuPG" / "bin" / "gpg.exe"
    else:
        # A Finder-launched app does not inherit the Homebrew PATH.
        yield from map(Path, ("/opt/homebrew/bin/gpg", "/usr/local/bin/gpg", "/usr/local/MacGPG2/bin/gpg", "/usr/bin/gpg"))


def find_gpg(configured: Optional[str] = None) -> str:
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which("gpg")
    if found:
        return found
    for path in _candidates():
        if path.is_file():
            return str(path.resolve())
    raise GpgNotFound("GnuPG (gpg) is not installed. Re-run the installer, or install it from https://gnupg.org.")


def _run(gpg: str, args, stdin: bytes, timeout: float = 120) -> subprocess.CompletedProcess:
    env = dict(os.environ, LC_ALL="C", LANGUAGE="C")  # stable, English error messages
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # no console flash under pythonw
    try:
        return subprocess.run(
            [gpg, "--batch", "--no-tty", "--quiet", *args],
            input=stdin,
            capture_output=True,
            timeout=timeout,
            env=env,
            **kwargs,
        )
    except FileNotFoundError:
        raise GpgNotFound(f"Could not run {gpg}.") from None
    except subprocess.TimeoutExpired:
        raise GpgError("gpg did not respond (is gpg-agent stuck? try: gpgconf --kill gpg-agent).") from None


def _check_passphrase(passphrase: str) -> bytes:
    if not passphrase or "\n" in passphrase or "\r" in passphrase:
        raise BadPassphrase("The passphrase is empty or contains a line break.")
    return passphrase.encode("utf-8") + b"\n"


def _error(proc: subprocess.CompletedProcess) -> GpgError:
    message = proc.stderr.decode("utf-8", "replace").strip()
    lowered = message.lower()
    if "bad session key" in lowered or "bad passphrase" in lowered or "decryption failed" in lowered:
        return BadPassphrase("Wrong GPG passphrase.")
    return GpgError(message or f"gpg exited with status {proc.returncode}")


def encrypt_secret(secret: str, passphrase: str, out_path: Path, gpg: str) -> None:
    """Encrypt ``secret`` to ``out_path`` (mode 0600), replacing it atomically."""
    # In loopback mode gpg reads the passphrase from the first line of stdin and the data from the rest.
    stdin = _check_passphrase(passphrase) + secret.encode("utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out_path.parent, prefix=".cred-", suffix=".tmp")
    os.close(fd)
    try:
        proc = _run(
            gpg,
            [
                "--yes", "--no-symkey-cache", "--pinentry-mode", "loopback", "--passphrase-fd", "0",
                "--symmetric", "--cipher-algo", "AES256",
                "--s2k-mode", "3", "--s2k-digest-algo", "SHA512", "--s2k-count", "65011712",
                "--output", tmp,
            ],
            stdin,
        )
        if proc.returncode != 0:
            raise _error(proc)
        os.chmod(tmp, 0o600)
        os.replace(tmp, out_path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def decrypt_cached(path: Path, gpg: str) -> Optional[str]:
    """Decrypt using a passphrase that gpg-agent has already cached; None if it hasn't."""
    proc = _run(gpg, ["--pinentry-mode", "error", "--decrypt", str(path)], b"", timeout=30)
    return _secret(proc.stdout) if proc.returncode == 0 else None


def decrypt_with_passphrase(path: Path, passphrase: str, gpg: str, *, cache: bool = True) -> str:
    """Decrypt with ``passphrase``. With ``cache=True``, gpg-agent remembers it (default TTL 10 min).

    ``--passphrase-fd`` hands the passphrase straight to gpg and bypasses the agent, so
    nothing gets cached. ``--command-fd`` answers the agent's loopback inquiry, so the
    agent caches the passphrase (wrong passphrases are not cached).
    """
    fd_option = "--command-fd" if cache else "--passphrase-fd"
    args = ["--pinentry-mode", "loopback", fd_option, "0", "--decrypt", str(path)]
    proc = _run(gpg, args, _check_passphrase(passphrase))
    if proc.returncode != 0:
        raise _error(proc)
    return _secret(proc.stdout)


def _secret(data: bytes) -> str:
    # Tolerate a trailing newline, as in files made with `echo pw > passwd.txt && gpg -c passwd.txt`.
    return data.decode("utf-8").rstrip("\r\n")


def unlock_db_password(
    path: Path, gpg: str, ask_passphrase: Callable[[int], Optional[str]]
) -> str:
    """Decrypt the DB password, asking for the passphrase only if gpg-agent hasn't cached it.

    ``ask_passphrase(attempt)`` returns the passphrase, or None if the user cancels.
    """
    if not path.is_file():
        raise GpgError(f"The database credential file is missing: {path}")
    cached = decrypt_cached(path, gpg)
    if cached is not None:
        return cached
    for attempt in range(MAX_PASSPHRASE_ATTEMPTS):
        passphrase = ask_passphrase(attempt)
        if passphrase is None:
            raise PassphraseCancelled("Cancelled.")
        try:
            return decrypt_with_passphrase(path, passphrase, gpg)
        except BadPassphrase:
            continue
    raise BadPassphrase("Wrong GPG passphrase.")
