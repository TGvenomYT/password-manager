"""The encrypted vault stored in MySQL.

Schema (version 2):

* ``vault_meta``: one row (id = 1) holding the scrypt parameters, the data key
  wrapped with the master-password-derived key, and the persistent counter used
  for the failed-unlock lockout.
* ``passwords``: one row per entry. ``password`` is a Fernet token made with
  the data key.

Older versions of this app stored the Fernet key in plaintext in a ``locker``
table next to a bcrypt hash of the master password, in two separate rows. The
first successful unlock migrates such a database. It verifies the master
password against the old bcrypt hash, generates a new data key, re-encrypts
every entry, wraps the new key, and deletes the old ``locker`` table, all in a
single transaction.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

from . import crypto

log = logging.getLogger(__name__)

SCHEMA_VERSION = 3  # 3: recovery key columns
MIN_MASTER_PASSWORD_LENGTH = 8
MAX_USERNAME_LENGTH = 255

# Lockout: the first FREE_ATTEMPTS failures are free. Each failure after that
# locks the vault for BASE_LOCKOUT_SECONDS, doubling every time, up to the cap.
FREE_ATTEMPTS = 5
BASE_LOCKOUT_SECONDS = 30
MAX_LOCKOUT_SECONDS = 3600


class VaultError(Exception):
    """Base class for vault errors that can be shown to the user."""


class WrongMasterPassword(VaultError):
    message = "Wrong master password."

    def __init__(self, failed_attempts: int, locked_for: float) -> None:
        self.failed_attempts = failed_attempts
        self.locked_for = locked_for
        super().__init__(self.message)


class WrongRecoveryKey(WrongMasterPassword):
    """Counts towards the same lockout as a wrong master password."""
    message = "Wrong recovery key."


class NoRecoveryKey(VaultError):
    pass


class VaultLocked(VaultError):
    def __init__(self, remaining: float) -> None:
        self.remaining = remaining
        super().__init__(f"Too many failed attempts. Try again in {format_duration(remaining)}.")


class VaultCorrupted(VaultError):
    pass


class WeakMasterPassword(VaultError):
    pass


def lockout_seconds(failed_attempts: int) -> int:
    if failed_attempts < FREE_ATTEMPTS:
        return 0
    return min(BASE_LOCKOUT_SECONDS * 2 ** (failed_attempts - FREE_ATTEMPTS), MAX_LOCKOUT_SECONDS)


def format_duration(seconds: float) -> str:
    seconds = max(1, int(seconds + 0.999))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def check_master_password_strength(password: str) -> None:
    if len(password) < MIN_MASTER_PASSWORD_LENGTH:
        raise WeakMasterPassword(
            f"The master password must be at least {MIN_MASTER_PASSWORD_LENGTH} characters."
        )
    if not password.strip():
        raise WeakMasterPassword("The master password cannot be only spaces.")


def _legacy_bcrypt_matches(password: str, hashed: str) -> bool:
    # bcrypt only ever used the first 72 bytes. bcrypt>=5 raises instead of
    # truncating, so truncate here to verify hashes made by older versions.
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


@dataclass(frozen=True)
class Entry:
    id: int
    username: str
    password: Optional[str]  # None if the entry can't be decrypted


class Vault:
    def __init__(
        self,
        conn,
        *,
        clock: Callable[[], float] = time.time,
        kdf_params: Callable[[], crypto.KdfParams] = crypto.new_kdf_params,
    ) -> None:
        self._conn = conn
        self._clock = clock
        self._new_kdf_params = kdf_params
        self._fernet: Optional[Fernet] = None
        self._data_key: Optional[bytes] = None

    # ------------------------------------------------------------------ schema

    def ensure_schema(self) -> None:
        """Create or upgrade tables. Non-destructive and safe to run on every start."""
        self._reconnect()
        cur = self._cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS vault_meta (
                id              TINYINT UNSIGNED NOT NULL PRIMARY KEY,
                schema_version  INT UNSIGNED     NOT NULL,
                kdf             VARCHAR(16)      NULL,
                kdf_salt        VARCHAR(64)      NULL,
                kdf_n           INT UNSIGNED     NULL,
                kdf_r           INT UNSIGNED     NULL,
                kdf_p           INT UNSIGNED     NULL,
                wrapped_key     TEXT             NULL,
                failed_attempts INT UNSIGNED     NOT NULL DEFAULT 0,
                locked_until    DOUBLE           NOT NULL DEFAULT 0,
                recovery_salt        VARCHAR(64) NULL,
                recovery_wrapped_key TEXT        NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute(
            "INSERT IGNORE INTO vault_meta (id, schema_version) VALUES (1, %s)", (SCHEMA_VERSION,)
        )
        meta_columns = self._columns("vault_meta")
        added = [f"ADD COLUMN {name} {sql}" for name, sql in
                 (("recovery_salt", "VARCHAR(64) NULL"), ("recovery_wrapped_key", "TEXT NULL"))
                 if name not in meta_columns]
        if added:  # vault made before recovery keys existed
            cur.execute("ALTER TABLE vault_meta " + ", ".join(added))
        cur.execute("UPDATE vault_meta SET schema_version = %s WHERE id = 1 AND schema_version < %s",
                    (SCHEMA_VERSION, SCHEMA_VERSION))
        if not self._table_exists("passwords"):
            cur.execute(
                """
                CREATE TABLE passwords (
                    id         INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    username   VARCHAR(255) NOT NULL,
                    `password` TEXT         NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        else:
            # Legacy table: no primary key, and VARCHAR(255) is too short for Fernet
            # tokens of passwords longer than about 127 bytes.
            columns = self._columns("passwords")
            alters = []
            if "id" not in columns:
                alters.append("ADD COLUMN id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")
            if columns.get("password") not in ("text", "mediumtext", "longtext"):
                alters.append("MODIFY `password` TEXT")
            if alters:
                cur.execute("ALTER TABLE passwords " + ", ".join(alters))
        self._conn.commit()
        cur.close()

    # ------------------------------------------------------------------- state

    @property
    def is_unlocked(self) -> bool:
        return self._fernet is not None

    def is_initialized(self) -> bool:
        return self._meta()["wrapped_key"] is not None

    def needs_master_password_setup(self) -> bool:
        """True if no master password exists yet (new vault, or legacy vault that never set one)."""
        if self.is_initialized():
            return False
        _, legacy_master = self._legacy_locker()
        return legacy_master is None

    def lockout_remaining(self) -> float:
        return max(0.0, float(self._meta()["locked_until"]) - self._clock())

    def has_recovery_key(self) -> bool:
        return self._meta()["recovery_wrapped_key"] is not None

    # ------------------------------------------------------------- lock/unlock

    def create(self, master_password: str) -> None:
        """Set the master password on a new vault, or on a legacy vault that never had one."""
        check_master_password_strength(master_password)
        if not self.needs_master_password_setup():
            raise VaultError("A master password is already set. Unlock the vault instead.")
        legacy_keys, _ = self._legacy_locker()
        self._initialize(master_password, legacy_keys)

    def unlock(self, master_password: str) -> None:
        remaining = self.lockout_remaining()
        if remaining > 0:
            raise VaultLocked(remaining)
        meta = self._meta()
        if meta["wrapped_key"] is not None:
            if meta["kdf"] != "scrypt":
                raise VaultCorrupted(f"Unsupported key derivation {meta['kdf']!r}.")
            params = crypto.KdfParams.from_db(meta["kdf_salt"], meta["kdf_n"], meta["kdf_r"], meta["kdf_p"])
            try:
                data_key = crypto.unwrap_key(meta["wrapped_key"], crypto.derive_kek(master_password, params))
            except InvalidToken:
                raise self._failed_attempt() from None
            self._open(data_key)
        else:
            legacy_keys, legacy_master = self._legacy_locker()
            if legacy_master is None:
                raise VaultError("No master password is set yet.")
            if not _legacy_bcrypt_matches(master_password, legacy_master):
                raise self._failed_attempt()
            self._initialize(master_password, legacy_keys)
        self._reset_failures()

    def lock(self) -> None:
        self._fernet = None
        self._data_key = None

    # ------------------------------------------------------------ recovery key

    def set_recovery_key(self, recovery_key: str) -> None:
        """Store a recovery key for the unlocked vault, replacing any earlier one."""
        if self._data_key is None:
            raise VaultError("The vault is locked.")
        salt = os.urandom(crypto.SALT_BYTES)
        wrapped = crypto.wrap_key(self._data_key, crypto.derive_recovery_kek(recovery_key, salt))
        self._reconnect()
        cur = self._cursor()
        cur.execute("UPDATE vault_meta SET recovery_salt = %s, recovery_wrapped_key = %s WHERE id = 1",
                    (base64.b64encode(salt).decode("ascii"), wrapped))
        self._conn.commit()
        cur.close()

    def recover(self, recovery_key: str, new_master_password: str) -> None:
        """Open the vault with the recovery key and replace the forgotten master password.
        The recovery key keeps working until a new one is saved."""
        remaining = self.lockout_remaining()
        if remaining > 0:
            raise VaultLocked(remaining)
        try:
            crypto.normalize_recovery_key(recovery_key)
        except ValueError as exc:  # malformed: not counted as a failed attempt
            raise VaultError(str(exc)) from None
        check_master_password_strength(new_master_password)
        meta = self._meta()
        if meta["recovery_wrapped_key"] is None:
            raise NoRecoveryKey("This vault has no recovery key, so its master password can't be reset.")
        salt = base64.b64decode(meta["recovery_salt"])
        try:
            data_key = crypto.unwrap_key(meta["recovery_wrapped_key"], crypto.derive_recovery_kek(recovery_key, salt))
        except InvalidToken:
            raise self._failed_attempt(WrongRecoveryKey) from None
        params = self._new_kdf_params()
        wrapped = crypto.wrap_key(data_key, crypto.derive_kek(new_master_password, params))
        self._reconnect()
        cur = self._cursor()
        try:
            cur.execute("SELECT recovery_wrapped_key FROM vault_meta WHERE id = 1 FOR UPDATE")
            (current,) = cur.fetchone()
            if current is None or _text(current) != _text(meta["recovery_wrapped_key"]):
                raise VaultError("The recovery key was changed in another window. Try again.")
            cur.execute(
                "UPDATE vault_meta SET kdf = 'scrypt', kdf_salt = %s, kdf_n = %s, kdf_r = %s, kdf_p = %s, "
                "wrapped_key = %s, failed_attempts = 0, locked_until = 0 WHERE id = 1",
                (params.salt_b64, params.n, params.r, params.p, wrapped),
            )
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise
        finally:
            cur.close()
        self._open(data_key)

    # ----------------------------------------------------------------- entries

    def add_entry(self, username: str, password: str) -> int:
        fernet = self._require_unlocked()
        username = username.strip()
        if not username:
            raise ValueError("Username cannot be empty.")
        if len(username) > MAX_USERNAME_LENGTH:
            raise ValueError(f"Username is longer than {MAX_USERNAME_LENGTH} characters.")
        if not password:
            raise ValueError("Password cannot be empty.")
        token = fernet.encrypt(password.encode("utf-8")).decode("ascii")
        self._reconnect()
        cur = self._cursor()
        cur.execute("INSERT INTO passwords (username, `password`) VALUES (%s, %s)", (username, token))
        self._conn.commit()
        entry_id = cur.lastrowid
        cur.close()
        return entry_id

    def entries(self) -> List[Entry]:
        fernet = self._require_unlocked()
        self._reconnect()
        cur = self._cursor()
        cur.execute("SELECT id, username, `password` FROM passwords ORDER BY username, id")
        rows = cur.fetchall()
        self._conn.commit()  # end the read snapshot so the next read sees fresh data
        cur.close()
        result = []
        for entry_id, username, token in rows:
            plaintext = _try_decrypt([fernet], token)
            result.append(
                Entry(entry_id, username or "", plaintext.decode("utf-8", "replace") if plaintext else None)
            )
        return result

    def delete_by_username(self, username: str) -> int:
        self._require_unlocked()
        self._reconnect()
        cur = self._cursor()
        cur.execute("DELETE FROM passwords WHERE username = %s", (username.strip(),))
        deleted = cur.rowcount
        self._conn.commit()
        cur.close()
        return deleted

    # ---------------------------------------------------------------- internal

    def _open(self, data_key: bytes) -> None:
        self._data_key = data_key
        self._fernet = Fernet(data_key)

    def _require_unlocked(self) -> Fernet:
        if self._fernet is None:
            raise VaultError("The vault is locked.")
        return self._fernet

    def _cursor(self, dictionary: bool = False):
        # Buffered, so helper queries never leave an "unread result" on the connection.
        return self._conn.cursor(buffered=True, dictionary=dictionary)

    def _reconnect(self) -> None:
        # MySQL drops idle connections (wait_timeout), so reconnect before each operation.
        self._conn.ping(reconnect=True, attempts=2, delay=1)

    def _meta(self) -> dict:
        self._reconnect()
        cur = self._cursor(dictionary=True)
        cur.execute(
            "SELECT kdf, kdf_salt, kdf_n, kdf_r, kdf_p, wrapped_key, failed_attempts, locked_until, "
            "recovery_salt, recovery_wrapped_key FROM vault_meta WHERE id = 1"
        )
        row = cur.fetchone()
        self._conn.commit()
        cur.close()
        if row is None:
            raise VaultCorrupted("vault_meta is missing its row. Restart the app to repair it.")
        return row

    def _table_exists(self, name: str) -> bool:
        cur = self._cursor()
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            (name,),
        )
        (count,) = cur.fetchone()
        cur.close()
        return bool(count)

    def _columns(self, table: str) -> dict:
        cur = self._cursor()
        cur.execute(
            "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            (table,),
        )
        rows = cur.fetchall()
        cur.close()
        return {_text(name).lower(): _text(dtype).lower() for name, dtype in rows}

    def _legacy_locker(self) -> Tuple[List[str], Optional[str]]:
        """Return (plaintext keys in insertion order, bcrypt master hash) from the old ``locker`` table."""
        self._reconnect()
        if not self._table_exists("locker"):
            return [], None
        columns = self._columns("locker")
        key_col = next((c for c in ("encryption_key", "encryption") if c in columns), None)
        master_col = "master_password" if "master_password" in columns else None
        if key_col is None and master_col is None:
            return [], None
        selected = ", ".join(f"`{c}`" if c else "NULL" for c in (key_col, master_col))
        cur = self._cursor()
        # The old table has no primary key, so InnoDB returns rows in insertion order.
        # The old app always used the first key, which is the one that matters.
        cur.execute(f"SELECT {selected} FROM locker")
        rows = cur.fetchall()
        self._conn.commit()
        cur.close()
        keys: List[str] = []
        master: Optional[str] = None
        for key, master_hash in rows:
            key = _text(key).strip() if key is not None else ""
            if key and key not in keys:
                keys.append(key)
            if master is None and master_hash is not None and _text(master_hash).strip():
                master = _text(master_hash).strip()
        return keys, master

    def _initialize(self, master_password: str, legacy_keys: Sequence[str]) -> None:
        """Generate a new data key, re-encrypt any legacy entries with it, and store it wrapped."""
        legacy = []
        for key in legacy_keys:
            try:
                legacy.append(Fernet(key.encode("ascii")))
            except (ValueError, UnicodeEncodeError):
                log.warning("Ignoring a malformed legacy encryption key.")
        data_key = Fernet.generate_key()
        fernet = Fernet(data_key)
        params = self._new_kdf_params()
        wrapped = crypto.wrap_key(data_key, crypto.derive_kek(master_password, params))

        self._reconnect()
        had_locker = self._table_exists("locker")
        cur = self._cursor()
        try:
            cur.execute("SELECT wrapped_key FROM vault_meta WHERE id = 1 FOR UPDATE")
            row = cur.fetchone()
            if row is None or row[0] is not None:
                raise VaultError("The vault was initialized by another window. Restart the app.")
            cur.execute("SELECT id, `password` FROM passwords FOR UPDATE")
            rows = cur.fetchall()
            if rows and not legacy:
                raise VaultCorrupted(
                    "This database has saved passwords but no encryption key, so they cannot be decrypted."
                )
            updates, unreadable = [], 0
            for entry_id, token in rows:
                plaintext = _try_decrypt(legacy, token)
                if plaintext is None:
                    unreadable += 1  # already unreadable in the old app; kept so the user can delete it
                    continue
                updates.append((fernet.encrypt(plaintext).decode("ascii"), entry_id))
            if updates:
                cur.executemany("UPDATE passwords SET `password` = %s WHERE id = %s", updates)
            cur.execute(
                "UPDATE vault_meta SET schema_version = %s, kdf = 'scrypt', kdf_salt = %s, kdf_n = %s, "
                "kdf_r = %s, kdf_p = %s, wrapped_key = %s, failed_attempts = 0, locked_until = 0 WHERE id = 1",
                (SCHEMA_VERSION, params.salt_b64, params.n, params.r, params.p, wrapped),
            )
            if had_locker:
                cur.execute("DELETE FROM locker")  # removes the plaintext key and old bcrypt hash
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise
        finally:
            cur.close()
        if had_locker:
            try:
                cur = self._cursor()
                cur.execute("DROP TABLE locker")
                cur.close()
            except Exception:  # the table is already empty; a leftover table is harmless
                log.warning("Could not drop the empty legacy locker table.", exc_info=True)
            log.info("Migrated legacy vault: %d entries re-encrypted, %d unreadable.", len(updates), unreadable)
        self._open(data_key)

    def _failed_attempt(self, error=WrongMasterPassword) -> WrongMasterPassword:
        """Persist one more failed unlock and return the error to raise."""
        self._reconnect()
        cur = self._cursor()
        try:
            cur.execute("SELECT failed_attempts FROM vault_meta WHERE id = 1 FOR UPDATE")
            failed = int(cur.fetchone()[0]) + 1
            wait = lockout_seconds(failed)
            cur.execute(
                "UPDATE vault_meta SET failed_attempts = %s, locked_until = %s WHERE id = 1",
                (failed, self._clock() + wait if wait else 0),
            )
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise
        finally:
            cur.close()
        return error(failed, wait)

    def _reset_failures(self) -> None:
        cur = self._cursor()
        cur.execute("UPDATE vault_meta SET failed_attempts = 0, locked_until = 0 WHERE id = 1")
        self._conn.commit()
        cur.close()


def _try_decrypt(keys: Sequence[Fernet], token) -> Optional[bytes]:
    if token is None:
        return None
    token_bytes = _text(token).strip().encode("ascii", "ignore")
    for key in keys:
        try:
            return key.decrypt(token_bytes)
        except InvalidToken:
            continue
    return None


def _text(value) -> str:
    return value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else str(value)
