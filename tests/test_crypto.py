import os
import unicodedata

import pytest
from cryptography.fernet import Fernet, InvalidToken

from password_manager import crypto
from password_manager.vault import format_duration, lockout_seconds

PARAMS = crypto.KdfParams(salt=os.urandom(16), n=2**10)


def test_wrap_unwrap_roundtrip():
    data_key = Fernet.generate_key()
    wrapped = crypto.wrap_key(data_key, crypto.derive_kek("correct horse", PARAMS))
    assert data_key.decode() not in wrapped
    assert crypto.unwrap_key(wrapped, crypto.derive_kek("correct horse", PARAMS)) == data_key


def test_wrong_password_is_rejected():
    wrapped = crypto.wrap_key(Fernet.generate_key(), crypto.derive_kek("correct horse", PARAMS))
    with pytest.raises(InvalidToken):
        crypto.unwrap_key(wrapped, crypto.derive_kek("correct horsE", PARAMS))


def test_salt_changes_the_key():
    other = crypto.KdfParams(salt=os.urandom(16), n=2**10)
    wrapped = crypto.wrap_key(Fernet.generate_key(), crypto.derive_kek("pw-12345678", PARAMS))
    with pytest.raises(InvalidToken):
        crypto.unwrap_key(wrapped, crypto.derive_kek("pw-12345678", other))


def test_unicode_normalization():
    composed = unicodedata.normalize("NFC", "pässwörd-é")
    decomposed = unicodedata.normalize("NFD", composed)
    assert composed != decomposed
    wrapped = crypto.wrap_key(Fernet.generate_key(), crypto.derive_kek(composed, PARAMS))
    crypto.unwrap_key(wrapped, crypto.derive_kek(decomposed, PARAMS))


def test_params_db_roundtrip():
    params = crypto.new_kdf_params()
    assert params.n == 2**17 and len(params.salt) == 16
    assert crypto.KdfParams.from_db(params.salt_b64, params.n, params.r, params.p) == params


def test_lockout_schedule():
    assert [lockout_seconds(n) for n in range(1, 5)] == [0, 0, 0, 0]
    assert [lockout_seconds(n) for n in range(5, 9)] == [30, 60, 120, 240]
    assert lockout_seconds(50) == 3600
    assert format_duration(90) == "1m 30s" and format_duration(0.2) == "1s"


def test_recovery_key_format_and_typing_forgiveness():
    key = crypto.new_recovery_key()
    groups = key.split("-")
    assert len(groups) == 5 and all(len(g) == 5 for g in groups)
    assert crypto.new_recovery_key() != key
    typed = " " + key.lower().replace("-", " ").replace("0", "o").replace("1", "l") + " "
    assert crypto.normalize_recovery_key(typed) == key.replace("-", "")
    salt = os.urandom(16)
    data_key = Fernet.generate_key()
    wrapped = crypto.wrap_key(data_key, crypto.derive_recovery_kek(key, salt))
    assert crypto.unwrap_key(wrapped, crypto.derive_recovery_kek(typed, salt)) == data_key


@pytest.mark.parametrize("bad", ["", "ABCDE-FGHJK", "U" * 25, "ABCDE-FGHJK-MNPQR-STVWX-YZ012-3"])
def test_malformed_recovery_key_is_rejected(bad):
    with pytest.raises(ValueError):
        crypto.normalize_recovery_key(bad)


def test_wrong_recovery_key_is_rejected():
    salt = os.urandom(16)
    wrapped = crypto.wrap_key(Fernet.generate_key(), crypto.derive_recovery_kek(crypto.new_recovery_key(), salt))
    with pytest.raises(InvalidToken):
        crypto.unwrap_key(wrapped, crypto.derive_recovery_kek(crypto.new_recovery_key(), salt))
