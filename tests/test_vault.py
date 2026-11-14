import bcrypt
import pytest
from cryptography.fernet import Fernet

from password_manager.vault import (
    FREE_ATTEMPTS, Vault, VaultCorrupted, VaultError, VaultLocked, WeakMasterPassword, WrongMasterPassword,
)

MASTER = "correct horse battery"


def make_vault(conn, fast_kdf, clock=None):
    kwargs = {"kdf_params": fast_kdf}
    if clock is not None:
        kwargs["clock"] = clock
    vault = Vault(conn, **kwargs)
    vault.ensure_schema()
    return vault


def dump_all_text(conn):
    """Every value stored in the database, for checking that no plaintext secret leaks."""
    cur = conn.cursor()
    cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")
    blobs = []
    for (table,) in cur.fetchall():
        cur.execute(f"SELECT * FROM `{table}`")
        blobs.extend(str(v) for row in cur.fetchall() for v in row)
    conn.commit()
    return "\n".join(blobs)


def create_legacy_schema(conn, entries, master=MASTER, with_key=True, with_master=True):
    """Reproduce what the old main2.py created: two half-empty locker rows and a plaintext key."""
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS passwords (username VARCHAR(255), password VARCHAR(255))")
    cur.execute("CREATE TABLE IF NOT EXISTS  locker(encryption_key char(255), master_password char(255))")
    key = Fernet.generate_key()
    if with_key:
        cur.execute("INSERT INTO locker (encryption_key)  VALUES (%s)", (key.decode(),))
    if with_master:
        hashed = bcrypt.hashpw(master.encode(), bcrypt.gensalt()).decode()
        cur.execute("INSERT INTO locker (master_password) VALUES (%s)", (hashed,))
    fer = Fernet(key)
    for user, pwd in entries:
        cur.execute("insert into passwords (username,password) values (%s,%s)", (user, fer.encrypt(pwd.encode()).decode()))
    conn.commit()
    return key


# ------------------------------------------------------------------ new vaults

def test_new_vault_lifecycle(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    assert vault.needs_master_password_setup()
    with pytest.raises(WeakMasterPassword):
        vault.create("short")
    vault.create(MASTER)
    assert vault.is_unlocked and not vault.needs_master_password_setup()

    long_password = "p" * 300  # VARCHAR(255) in the old schema could not store this
    vault.add_entry("  gmail  ", "hunter2")
    vault.add_entry("bank", long_password)
    vault.add_entry("bank", "second")

    reopened = make_vault(conn, fast_kdf)
    with pytest.raises(VaultError):
        reopened.entries()  # locked
    reopened.unlock(MASTER)
    got = [(e.username, e.password) for e in reopened.entries()]
    assert got == [("bank", long_password), ("bank", "second"), ("gmail", "hunter2")]

    assert reopened.delete_by_username("bank") == 2
    assert reopened.delete_by_username("nobody") == 0
    assert [e.username for e in reopened.entries()] == ["gmail"]


def test_no_plaintext_secrets_in_database(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    vault.add_entry("site", "TopSecretValue!")
    data_key = vault._fernet._signing_key + vault._fernet._encryption_key
    stored = dump_all_text(conn)
    assert "TopSecretValue!" not in stored
    assert MASTER not in stored
    import base64
    assert base64.urlsafe_b64encode(data_key).decode() not in stored


def test_create_twice_is_refused(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    with pytest.raises(VaultError):
        make_vault(conn, fast_kdf).create("another password")


def test_ensure_schema_is_idempotent(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    vault.add_entry("a", "b")
    vault.ensure_schema()
    vault.ensure_schema()
    assert [e.password for e in vault.entries()] == ["b"]


# ---------------------------------------------------------------------- lockout

def test_lockout_is_persistent_and_resets(conn, fast_kdf, clock):
    make_vault(conn, fast_kdf, clock).create(MASTER)
    vault = make_vault(conn, fast_kdf, clock)
    for attempt in range(1, FREE_ATTEMPTS):
        with pytest.raises(WrongMasterPassword) as err:
            vault.unlock("wrong password")
        assert err.value.failed_attempts == attempt and err.value.locked_for == 0

    # Restarting the app (new Vault object) must not reset the counter.
    vault = make_vault(conn, fast_kdf, clock)
    with pytest.raises(WrongMasterPassword) as err:
        vault.unlock("wrong password")
    assert err.value.locked_for == 30

    with pytest.raises(VaultLocked):
        vault.unlock(MASTER)  # even the right password waits out the lockout
    clock.now += 31
    with pytest.raises(WrongMasterPassword) as err:
        vault.unlock("wrong again")
    assert err.value.locked_for == 60  # doubles

    clock.now += 61
    vault.unlock(MASTER)
    assert vault.lockout_remaining() == 0
    with pytest.raises(WrongMasterPassword) as err:
        make_vault(conn, fast_kdf, clock).unlock("nope")
    assert err.value.failed_attempts == 1  # counter reset after success


def test_failed_attempts_never_delete_data(conn, fast_kdf, clock):
    vault = make_vault(conn, fast_kdf, clock)
    vault.create(MASTER)
    vault.add_entry("keep", "me")
    for _ in range(12):
        clock.now += 10_000
        with pytest.raises(WrongMasterPassword):
            vault.unlock("bad")
    clock.now += 10_000
    vault.unlock(MASTER)
    assert [e.password for e in vault.entries()] == ["me"]


# -------------------------------------------------------------------- migration

def test_legacy_vault_is_migrated(conn, fast_kdf):
    entries = [("gmail", "hunter2"), ("bank", "x" * 120)]
    legacy_key = create_legacy_schema(conn, entries)

    vault = make_vault(conn, fast_kdf)
    assert not vault.needs_master_password_setup()  # the old master password still applies
    with pytest.raises(WrongMasterPassword):
        vault.unlock("not the master")
    vault.unlock(MASTER)

    assert sorted((e.username, e.password) for e in vault.entries()) == sorted(entries)
    stored = dump_all_text(conn)
    assert legacy_key.decode() not in stored, "plaintext key must be gone"
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'locker'")
    assert cur.fetchone()[0] == 0
    # Entries were re-encrypted under a new key, so the leaked legacy key no longer opens them.
    cur.execute("SELECT `password` FROM passwords")
    old = Fernet(legacy_key)
    for (token,) in cur.fetchall():
        with pytest.raises(Exception):
            old.decrypt(token.encode())
    conn.commit()

    again = make_vault(conn, fast_kdf)
    again.unlock(MASTER)
    assert len(again.entries()) == 2


def test_legacy_vault_without_master_password(conn, fast_kdf):
    create_legacy_schema(conn, [("site", "pw")], with_master=False)
    vault = make_vault(conn, fast_kdf)
    assert vault.needs_master_password_setup()
    vault.create(MASTER)
    assert [(e.username, e.password) for e in vault.entries()] == [("site", "pw")]


def test_legacy_vault_with_missing_key_and_entries_is_reported(conn, fast_kdf):
    create_legacy_schema(conn, [("site", "pw")], with_key=False)
    vault = make_vault(conn, fast_kdf)
    with pytest.raises(VaultCorrupted):
        vault.unlock(MASTER)


def test_legacy_unreadable_entry_is_kept_and_flagged(conn, fast_kdf):
    create_legacy_schema(conn, [("good", "pw")])
    cur = conn.cursor()
    cur.execute("INSERT INTO passwords (username, password) VALUES ('broken', 'not-a-token')")
    conn.commit()
    vault = make_vault(conn, fast_kdf)
    vault.unlock(MASTER)
    assert {e.username: e.password for e in vault.entries()} == {"good": "pw", "broken": None}
