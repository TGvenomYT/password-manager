import os

import pytest

from password_manager import credentials


@pytest.fixture
def gpg():
    if os.environ.get("PM_SKIP_GPG_TESTS"):
        pytest.skip("PM_SKIP_GPG_TESTS is set")
    try:
        return credentials.find_gpg()
    except credentials.GpgNotFound:
        pytest.skip("gpg not installed")


def test_encrypt_decrypt_roundtrip(gpg, tmp_path):
    path = tmp_path / "cred.gpg"
    credentials.encrypt_secret("s3cr3t-db-pass_XYZ", "pass phrase 1", path, gpg)
    assert path.read_bytes()[:1] != b"s"
    if os.name != "nt":
        assert oct(path.stat().st_mode & 0o777) == "0o600"
    # Wrong passphrase first, while nothing is cached for this file's salt.
    with pytest.raises(credentials.BadPassphrase):
        credentials.decrypt_with_passphrase(path, "wrong", gpg, cache=False)
    assert credentials.decrypt_with_passphrase(path, "pass phrase 1", gpg, cache=False) == "s3cr3t-db-pass_XYZ"


def test_unlock_asks_and_retries(gpg, tmp_path):
    path = tmp_path / "cred.gpg"
    credentials.encrypt_secret("value", "right passphrase", path, gpg)
    answers = iter(["wrong", "right passphrase"])
    asked = []

    def ask(attempt):
        asked.append(attempt)
        return next(answers)

    assert credentials.decrypt_cached(path, gpg) is None
    assert credentials.unlock_db_password(path, gpg, ask) == "value"
    assert asked == [0, 1]
    # The right passphrase is now cached by gpg-agent, so the next launch doesn't ask.
    assert credentials.decrypt_cached(path, gpg) == "value"
    assert credentials.unlock_db_password(path, gpg, lambda attempt: pytest.fail("asked again")) == "value"


def test_unlock_cancel(gpg, tmp_path):
    path = tmp_path / "cred.gpg"
    credentials.encrypt_secret("value", "another passphrase", path, gpg)
    with pytest.raises(credentials.PassphraseCancelled):
        credentials.unlock_db_password(path, gpg, lambda attempt: None)


def test_newline_in_passphrase_rejected(gpg, tmp_path):
    with pytest.raises(credentials.BadPassphrase):
        credentials.encrypt_secret("value", "line\nbreak", tmp_path / "x.gpg", gpg)
