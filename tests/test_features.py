import re
from types import SimpleNamespace

import pytest

from password_manager import audit, csvio, generator


def test_random_password_has_every_chosen_group():
    for _ in range(50):
        pw = generator.random_password(12)
        assert len(pw) == 12
        assert re.search(r"[a-z]", pw) and re.search(r"[A-Z]", pw) and re.search(r"[0-9]", pw)
        assert any(c in generator.SYMBOLS for c in pw)
        assert not set(pw) & set("Il1O0'\\\"")
    plain = generator.random_password(30, digits=False, symbols=False)
    assert plain.isalpha() and len(plain) == 30
    assert len(generator.random_password(3)) == generator.MIN_LENGTH
    assert len(generator.random_password(999)) == generator.MAX_LENGTH


def test_memorable_password_shape_and_strength():
    for _ in range(50):
        pw = generator.memorable_password()
        assert re.fullmatch(r"[a-zA-Z0-9]{6}-[a-zA-Z0-9]{6}-[a-zA-Z0-9]{6}", pw)
        assert re.search(r"[A-Z]", pw) and re.search(r"[0-9]", pw)
        assert audit.strength(pw) == 4
    assert generator.memorable_password() != generator.memorable_password()


@pytest.mark.parametrize("password, score", [
    ("", 0), ("password", 0), ("Password", 0), ("abc", 0), ("aaaaaaaaaaaa", 0),
    ("hunter22", 1), ("Summer2024", 2), ("x7#Kp2!vQz9", 3), ("correct horse battery", 4),
    ("x7#Kp2!vQz9@Lm4&", 4),
])
def test_strength(password, score):
    assert audit.strength(password) == score


def test_reused_lists_the_other_entries():
    entries = [SimpleNamespace(id=i, password=pw) for i, pw in enumerate(["a1", "b2", "a1", None, "a1"])]
    assert audit.reused(entries) == {0: [2, 4], 2: [0, 4], 4: [0, 2]}


@pytest.mark.parametrize("header, row", [
    ("name,url,username,password,note", "GitHub,https://github.com,me,pw1,my note"),               # Chrome
    ("Title,URL,Username,Password,Notes,OTPAuth", "GitHub,https://github.com,me,pw1,my note,"),     # Safari
    ("folder,favorite,type,name,notes,fields,reminder,login_uri,login_username,login_password,login_totp",
     ",,login,GitHub,my note,,,https://github.com,me,pw1,"),                                       # Bitwarden
])
def test_csv_import_formats(tmp_path, header, row):
    path = tmp_path / "export.csv"
    path.write_text(header + "\n" + row + "\nNoPassword,https://x.test,me,,\n", encoding="utf-8")
    assert csvio.read_csv(path) == [{"title": "GitHub", "website": "https://github.com", "username": "me",
                                     "password": "pw1", "notes": "my note", "totp": ""}]


def test_csv_import_needs_a_password_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("name,url\nx,y\n", encoding="utf-8")
    with pytest.raises(ValueError):
        csvio.read_csv(path)


def test_csv_export_round_trip(tmp_path):
    from password_manager.vault import Entry
    entries = [Entry(1, "me", 'p,w"1', title="GitHub", website="https://github.com", notes="line1\nline2"),
               Entry(2, "x", None, title="Broken")]
    path = tmp_path / "out.csv"
    assert csvio.write_csv(path, entries) == 1
    assert csvio.read_csv(path) == [{"title": "GitHub", "website": "https://github.com", "username": "me",
                                     "password": 'p,w"1', "notes": "line1\nline2", "totp": ""}]
