import bcrypt
import pytest
from cryptography.fernet import Fernet

from password_manager import crypto
from password_manager.vault import (
    FREE_ATTEMPTS, SCHEMA_VERSION, NoRecoveryKey, Vault, VaultCorrupted, VaultError, VaultLocked, WeakMasterPassword,
    WrongMasterPassword, WrongRecoveryKey,
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


# ----------------------------------------------------------------- recovery key

def test_recovery_key_replaces_a_forgotten_master_password(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    vault.add_entry("bank", "s3cret")
    assert not vault.has_recovery_key()
    key = crypto.new_recovery_key()
    vault.set_recovery_key(key)
    assert vault.has_recovery_key()

    forgot = make_vault(conn, fast_kdf)
    with pytest.raises(WeakMasterPassword):
        forgot.recover(key, "short")
    forgot.recover(key.lower().replace("-", " "), "brand new password")
    assert [(e.username, e.password) for e in forgot.entries()] == [("bank", "s3cret")]

    later = make_vault(conn, fast_kdf)
    with pytest.raises(WrongMasterPassword):
        later.unlock(MASTER)  # the old master password no longer works
    later.unlock("brand new password")
    assert [e.password for e in later.entries()] == ["s3cret"]
    make_vault(conn, fast_kdf).recover(key, "third password!")  # the key keeps working


def test_new_recovery_key_replaces_the_old_one(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    old, new = crypto.new_recovery_key(), crypto.new_recovery_key()
    vault.set_recovery_key(old)
    vault.set_recovery_key(new)
    with pytest.raises(WrongRecoveryKey):
        make_vault(conn, fast_kdf).recover(old, "brand new password")
    make_vault(conn, fast_kdf).recover(new, "brand new password")


def test_recovery_needs_an_unlocked_vault_to_set_and_a_key_to_use(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    locked = make_vault(conn, fast_kdf)
    with pytest.raises(VaultError):
        locked.set_recovery_key(crypto.new_recovery_key())
    with pytest.raises(NoRecoveryKey):
        locked.recover(crypto.new_recovery_key(), "brand new password")
    with pytest.raises(VaultError) as err:
        locked.recover("not a key", "brand new password")
    assert not isinstance(err.value, WrongMasterPassword)  # a typo isn't a failed attempt


def test_wrong_recovery_keys_count_towards_the_lockout(conn, fast_kdf, clock):
    vault = make_vault(conn, fast_kdf, clock)
    vault.create(MASTER)
    key = crypto.new_recovery_key()
    vault.set_recovery_key(key)
    other = make_vault(conn, fast_kdf, clock)
    for _ in range(FREE_ATTEMPTS - 1):
        with pytest.raises(WrongRecoveryKey):
            other.recover(crypto.new_recovery_key(), "brand new password")
    with pytest.raises(WrongRecoveryKey) as err:
        other.recover(crypto.new_recovery_key(), "brand new password")
    assert err.value.locked_for == 30
    with pytest.raises(VaultLocked):
        other.recover(key, "brand new password")
    clock.now += 31
    other.recover(key, "brand new password")
    assert other.lockout_remaining() == 0


def test_recovery_key_is_never_stored_in_plaintext(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    key = crypto.new_recovery_key()
    vault.set_recovery_key(key)
    stored = dump_all_text(conn)
    assert key not in stored and key.replace("-", "") not in stored


def test_vault_from_before_recovery_keys_is_upgraded(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    vault.add_entry("old", "entry")
    cur = conn.cursor()
    cur.execute("ALTER TABLE vault_meta DROP COLUMN recovery_salt, DROP COLUMN recovery_wrapped_key")
    cur.execute("UPDATE vault_meta SET schema_version = 2")
    conn.commit()
    upgraded = make_vault(conn, fast_kdf)  # ensure_schema adds the columns back
    upgraded.unlock(MASTER)
    assert not upgraded.has_recovery_key()
    upgraded.set_recovery_key(crypto.new_recovery_key())
    assert [e.password for e in upgraded.entries()] == ["entry"]
    cur.execute("SELECT schema_version FROM vault_meta")
    assert cur.fetchone()[0] == SCHEMA_VERSION
    conn.commit()



# ------------------------------------------------------------ entries (schema 4)

def test_entries_keep_every_field_encrypted(conn, fast_kdf, clock):
    vault = make_vault(conn, fast_kdf, clock)
    vault.create(MASTER)
    entry_id = vault.add_entry("ann@mail.test", "S3cret!pw", title="GitHub", website="https://www.github.com/login",
                               notes="2FA codes in the drawer")
    (entry,) = vault.entries()
    assert (entry.id, entry.title, entry.username, entry.password, entry.website, entry.notes) == (
        entry_id, "GitHub", "ann@mail.test", "S3cret!pw", "https://www.github.com/login", "2FA codes in the drawer")
    assert entry.created_at == entry.updated_at == clock.now and not entry.favorite and entry.deleted_at is None
    stored = dump_all_text(conn)
    for secret in ("GitHub", "ann@mail.test", "S3cret!pw", "github.com", "2FA codes"):
        assert secret not in stored

    clock.now += 60
    vault.update_entry(entry_id, title="GitHub (work)", username="ann", password="N3w!pass", website="github.com")
    (entry,) = vault.entries()
    assert (entry.title, entry.username, entry.password, entry.notes) == ("GitHub (work)", "ann", "N3w!pass", "")
    assert entry.updated_at == clock.now and entry.created_at == clock.now - 60

    with pytest.raises(ValueError):
        vault.add_entry("", "pw")                 # needs a title, website or user name
    with pytest.raises(ValueError):
        vault.add_entry("x", "", title="Empty")    # needs a password


def test_name_falls_back_to_website_then_username():
    from password_manager.vault import Entry
    assert Entry(1, "u", "p", title="T").name == "T"
    assert Entry(1, "u", "p", website="https://www.Example.com:8443/a?b").name == "example.com"
    assert Entry(1, "u", "p").name == "u"


def test_favourites_trash_and_restore(conn, fast_kdf, clock):
    from password_manager.vault import TRASH_DAYS
    vault = make_vault(conn, fast_kdf, clock)
    vault.create(MASTER)
    a = vault.add_entry("a", "pw-a", title="Alpha")
    b = vault.add_entry("b", "pw-b", title="Beta")
    vault.set_favorite(a, True)
    assert [e.favorite for e in vault.entries()] == [True, False]

    vault.trash_entry(b)
    assert [e.title for e in vault.entries()] == ["Alpha"]
    assert [e.title for e in vault.entries(trash=True)] == ["Beta"]
    vault.restore_entry(b)
    assert [e.title for e in vault.entries()] == ["Alpha", "Beta"]

    vault.trash_entry(b)
    clock.now += TRASH_DAYS * 86400 + 1
    reopened = make_vault(conn, fast_kdf, clock)
    reopened.unlock(MASTER)                       # unlocking purges old trash
    assert reopened.entries(trash=True) == [] and len(reopened.entries()) == 1

    reopened.trash_entry(a)
    assert reopened.empty_trash() == 1 and reopened.entries() == []


def test_import_skips_exact_duplicates(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    vault.add_entry("me", "pw1", title="GitHub", website="https://github.com")
    rows = [{"title": "GitHub", "website": "https://github.com", "username": "me", "password": "pw1", "notes": ""},
            {"title": "Bank", "website": "", "username": "me", "password": "pw2", "notes": "pin 0000"},
            {"title": "Bank", "website": "", "username": "me", "password": "pw2", "notes": "pin 0000"}]
    assert vault.import_entries(rows) == (1, 2)
    assert [e.title for e in vault.entries()] == ["Bank", "GitHub"]


def test_change_master_password(conn, fast_kdf, clock):
    vault = make_vault(conn, fast_kdf, clock)
    vault.create(MASTER)
    vault.add_entry("me", "pw", title="Site")
    key = crypto.new_recovery_key()
    vault.set_recovery_key(key)
    with pytest.raises(WrongMasterPassword):
        vault.change_master_password("not it", "a new password")
    with pytest.raises(WeakMasterPassword):
        vault.change_master_password(MASTER, "short")
    vault.change_master_password(MASTER, "a new password")
    other = make_vault(conn, fast_kdf, clock)
    with pytest.raises(WrongMasterPassword):
        other.unlock(MASTER)
    other.unlock("a new password")
    assert other.lockout_remaining() == 0 and [e.password for e in other.entries()] == ["pw"]
    make_vault(conn, fast_kdf, clock).recover(key, "third password")  # the recovery key still works


def test_schema3_entries_are_upgraded_on_unlock(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    token = vault._fernet.encrypt(b"old-pw").decode()
    cur = conn.cursor()
    cur.execute("INSERT INTO passwords (username, `password`) VALUES ('Gmail', %s)", (token,))
    conn.commit()
    reopened = make_vault(conn, fast_kdf)
    reopened.unlock(MASTER)
    (entry,) = reopened.entries()
    assert (entry.title, entry.username, entry.password) == ("Gmail", "Gmail", "old-pw")
    cur.execute("SELECT username, `password`, data IS NOT NULL FROM passwords")
    assert cur.fetchall() == [("", "", 1)]       # nothing readable left in the old columns
    conn.commit()


# ------------------------------------------------- 2FA, secure notes, history, restore

def test_password_history_keeps_earlier_passwords(conn, fast_kdf, clock):
    from password_manager.vault import HISTORY_LIMIT
    vault = make_vault(conn, fast_kdf, clock)
    vault.create(MASTER)
    entry_id = vault.add_entry("me", "first-pass", title="Site")
    for i in range(HISTORY_LIMIT + 2):
        clock.now += 10
        vault.update_entry(entry_id, title="Site", username="me", password=f"pass-{i}")
    vault.update_entry(entry_id, title="Site renamed", username="me", password=f"pass-{HISTORY_LIMIT + 1}")
    (entry,) = vault.entries()
    assert entry.password == f"pass-{HISTORY_LIMIT + 1}" and entry.title == "Site renamed"
    assert [h["password"] for h in entry.history][:2] == [f"pass-{HISTORY_LIMIT}", f"pass-{HISTORY_LIMIT - 1}"]
    assert len(entry.history) == HISTORY_LIMIT  # a rename alone doesn't add history
    assert "first-pass" not in dump_all_text(conn)


def test_secure_notes_and_2fa(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    vault.add_entry("", "", title="Bank PIN", notes="4321", kind="note")
    vault.add_entry("me", "pw", title="GitHub", totp="otpauth://totp/GitHub:me?secret=JBSWY3DPEHPK3PXP")
    with pytest.raises(ValueError, match="2FA"):
        vault.add_entry("me", "pw", title="X", totp="not a key!")
    with pytest.raises(ValueError):
        vault.add_entry("", "", title="", notes="text", kind="note")
    note, login = vault.entries()
    assert (note.kind, note.notes, note.password) == ("note", "4321", "")
    assert login.totp.startswith("otpauth://") and "JBSWY3DP" not in dump_all_text(conn)


def test_import_keeps_2fa_favourites_and_history(conn, fast_kdf):
    vault = make_vault(conn, fast_kdf)
    vault.create(MASTER)
    added, skipped = vault.import_entries([
        {"title": "GitHub", "username": "me", "password": "pw", "totp": "JBSWY3DPEHPK3PXP", "favorite": True,
         "history": [{"password": "older", "changed": 5}]},
        {"title": "Steam", "username": "me", "password": "pw2", "totp": "steam://ABC"},  # unusable 2FA: kept anyway
    ])
    assert (added, skipped) == (2, 0)
    github, steam = vault.entries()
    assert github.favorite and github.totp == "JBSWY3DPEHPK3PXP" and github.history[0]["password"] == "older"
    assert steam.totp == "" and steam.password == "pw2"
