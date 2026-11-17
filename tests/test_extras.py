import hashlib
from types import SimpleNamespace

import pytest

from password_manager import backup, crypto, pwned, totp

RFC_KEY = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32 of "12345678901234567890" (RFC 6238 test key)


@pytest.mark.parametrize("at, code", [(59, "94287082"), (1111111109, "07081804"), (1234567890, "89005924"),
                                      (2000000000, "69279037")])
def test_totp_matches_rfc6238(at, code):
    spec = totp.parse(f"otpauth://totp/Test:me?secret={RFC_KEY}&digits=8")
    assert spec.code(at) == code


def test_totp_parsing():
    spec = totp.parse("otpauth://totp/GitHub:alex?secret=JBSWY3DPEHPK3PXP&issuer=GitHub&period=60")
    assert (spec.issuer, spec.account, spec.period, spec.digits) == ("GitHub", "alex", 60, 6)
    assert totp.parse("jbsw y3dp ehpk 3pxp").secret == spec.secret
    assert len(spec.code(0)) == 6 and spec.remaining(65) == 55
    for bad in ("", "not base32!", "ABCD", "otpauth://hotp/x?secret=JBSWY3DPEHPK3PXP",
                "otpauth://totp/x?secret=JBSWY3DPEHPK3PXP&digits=4"):
        assert not totp.is_valid(bad)


def test_pwned_sends_only_a_hash_prefix():
    leaked, safe = "password123", "x7#Kp2!vQz9@Lm4&Rt"
    sent = []

    def fake_fetch(prefix):
        sent.append(prefix)
        suffix = hashlib.sha1(leaked.encode()).hexdigest().upper()[5:]
        return f"{suffix}:2045\nABCDEF0123456789ABCDEF0123456789ABC:0\n" if hashlib.sha1(
            leaked.encode()).hexdigest().upper().startswith(prefix) else "0000000000000000000000000000000000A:3\n"

    assert pwned.check([leaked, safe, leaked], fetch=fake_fetch) == {leaked: 2045, safe: 0}
    assert all(len(p) == 5 for p in sent) and len(sent) == 2


def test_backup_round_trip(tmp_path):
    fast = lambda: crypto.KdfParams(salt=b"\0" * 16, n=2**10)  # noqa: E731
    entry = SimpleNamespace(title="GitHub", username="alex", password="pw", website="github.com", notes="n",
                            totp=RFC_KEY, kind="login", favorite=True, history=({"password": "old", "changed": 1.0},))
    path = tmp_path / "vault.pmbackup"
    assert backup.write(path, [entry, SimpleNamespace(password=None)], "backup-password", fast) == 1
    assert "github" not in path.read_text().lower()
    (item,) = backup.read(path, "backup-password")
    assert item["title"] == "GitHub" and item["totp"] == RFC_KEY and item["favorite"] and item["history"][0]["password"] == "old"
    with pytest.raises(ValueError, match="Wrong backup password"):
        backup.read(path, "not the password")
    with pytest.raises(ValueError):
        backup.write(path, [entry], "short", fast)


def test_leak_check_uses_the_bundled_certificate_list(monkeypatch):
    import certifi
    seen = {}
    real = pwned.ssl.create_default_context

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(pwned.ssl, "create_default_context", spy)
    pwned.tls_context()
    assert seen.get("cafile") == certifi.where()
