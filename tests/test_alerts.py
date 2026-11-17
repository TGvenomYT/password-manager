"""Security alert emails: what they say, where they go, and how the app sends them."""

import os
import smtplib
import time

import pytest

from password_manager import alerts

ADDRESS = "alex@gmail.com"


class FakeSMTP:
    """Records what would have been sent instead of talking to a mail server."""

    def __init__(self, fail=None):
        self.fail = fail
        self.logins = []
        self.sent = []

    def __call__(self, provider):
        self.provider = provider
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.tls = True

    def login(self, user, password):
        if self.fail:
            raise self.fail
        self.logins.append((user, password))

    def send_message(self, message, from_addr=None, to_addrs=None):
        self.sent.append((message, from_addr, to_addrs))


class FakeKeyring:
    def __init__(self):
        self.store = {}

    def set_password(self, service, user, password):
        self.store[(service, user)] = password

    def get_password(self, service, user):
        return self.store.get((service, user))

    def delete_password(self, service, user):
        del self.store[(service, user)]


@pytest.fixture
def keyring(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr(alerts, "_keyring", lambda: fake)
    return fake


@pytest.mark.parametrize("address, host", [
    ("alex@gmail.com", "smtp.gmail.com"), ("Alex@GMAIL.com", "smtp.gmail.com"),
    ("alex@icloud.com", "smtp.mail.me.com"), ("alex@yahoo.com", "smtp.mail.yahoo.com"),
])
def test_provider_for_supported_addresses(address, host):
    assert alerts.provider_for(address).host == host


@pytest.mark.parametrize("address, message", [
    ("", "Enter an email address"), ("alex", "Enter an email address"), ("alex@gmail", "Enter an email address"),
    ("alex@example.com", "Gmail, iCloud Mail and Yahoo Mail"),
])
def test_provider_for_rejects_other_addresses(address, message):
    with pytest.raises(alerts.AlertError, match=message):
        alerts.provider_for(address)


def test_app_password_spaces_are_dropped():
    assert alerts.clean_app_password(" abcd efgh\tijkl mnop ") == "abcdefghijklmnop"


@pytest.mark.parametrize("kind, facts", [
    ("test", {}), ("lockout", {"attempts": 5, "locked_for": 30}), ("recovered", {}),
    ("password_changed", {}), ("recovery_key", {}), ("leaks", {"count": 3}),
])
def test_every_alert_goes_to_the_sender_only(kind, facts):
    message = alerts.compose(ADDRESS, kind, computer="Studio <Mac>", **facts)
    assert message["To"] == ADDRESS
    assert message["From"] == f"Password Manager <{ADDRESS}>"
    assert message["Cc"] is None and message["Bcc"] is None
    assert message["Subject"].startswith("Password Manager: ")
    text = message.get_body(("plain",)).get_content()
    page = message.get_body(("html",)).get_content()
    assert "Studio <Mac>" in text and "Studio &lt;Mac&gt;" in page  # escaped in the HTML part
    assert "never contain your passwords" in text
    [icon] = [part for part in message.walk() if part.get_content_type() == "image/png"]
    assert icon["Content-ID"][1:-1] in page and icon.get_content().startswith(b"\x89PNG")
    assert icon.get_content_disposition() == "inline"


def test_lockout_and_leak_details():
    lockout = alerts.compose(ADDRESS, "lockout", attempts=6, locked_for=60)
    assert lockout["Subject"] == "Password Manager: Wrong master password entered 6 times"
    assert "for 1 minute," in lockout.get_body(("plain",)).get_content()
    leaks = alerts.compose(ADDRESS, "leaks", count=1)
    assert leaks["Subject"] == "Password Manager: 1 of your passwords appeared in data leaks"
    with pytest.raises(ValueError):
        alerts.compose(ADDRESS, "nonsense")


def test_send_signs_in_and_sends_to_the_same_address():
    smtp = FakeSMTP()
    alerts.send(ADDRESS, "abcd efgh ijkl mnop", alerts.compose(ADDRESS, "test"), smtp_factory=smtp)
    assert smtp.logins == [(ADDRESS, "abcdefghijklmnop")]
    [(message, sender, recipients)] = smtp.sent
    assert sender == ADDRESS and recipients == [ADDRESS]


def test_send_refuses_a_message_for_someone_else():
    smtp = FakeSMTP()
    message = alerts.compose(ADDRESS, "test")
    message.replace_header("To", "someone@gmail.com")
    with pytest.raises(alerts.AlertError, match="your own address"):
        alerts.send(ADDRESS, "pw", message, smtp_factory=smtp)
    assert smtp.sent == []


@pytest.mark.parametrize("error, message", [
    (smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted"), "didn't accept that app password"),
    (TimeoutError("timed out"), "Couldn't reach Gmail"),
    (smtplib.SMTPDataError(550, b"no"), "didn't send the email"),
])
def test_send_explains_failures(error, message):
    with pytest.raises(alerts.AlertError, match=message):
        alerts.send(ADDRESS, "pw", alerts.compose(ADDRESS, "test"), smtp_factory=FakeSMTP(fail=error))


def test_app_password_is_kept_in_the_password_store(keyring):
    alerts.save_password(ADDRESS, "abcd efgh ijkl mnop")
    assert keyring.store == {(alerts.KEYRING_SERVICE, ADDRESS): "abcdefghijklmnop"}
    assert alerts.load_password(ADDRESS) == "abcdefghijklmnop"
    alerts.forget_password(ADDRESS)
    alerts.forget_password(ADDRESS)  # already gone: no error
    with pytest.raises(alerts.AlertError, match="missing"):
        alerts.load_password(ADDRESS)


def test_throttle():
    now = [1000.0]
    throttle = alerts.Throttle(600, lambda: now[0])
    assert throttle.allow("lockout") and not throttle.allow("lockout") and throttle.allow("leaks")
    now[0] += 601
    assert throttle.allow("lockout")


# --------------------------------------------------------------- in the app

@pytest.fixture
def backend(tmp_path, monkeypatch, keyring):
    pytest.importorskip("PySide6.QtGui", reason="PySide6 isn't installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    from password_manager import backend as backend_module
    from password_manager import config as cfgmod

    QGuiApplication.instance() or QGuiApplication([])
    monkeypatch.setattr(cfgmod, "config_dir", lambda: tmp_path)
    sent = []
    monkeypatch.setattr(alerts, "send", lambda address, password, message, smtp_factory=None:
                        sent.append((address, password, message)))
    b = backend_module.Backend()
    b.sent = sent
    b.messages = []
    b.dialogMessage.connect(lambda text, is_error: b.messages.append((text, is_error)))
    yield b
    b.shutdown()


def settle(backend, until):
    from PySide6.QtCore import QCoreApplication

    for _ in range(200):
        QCoreApplication.processEvents()
        if until():
            return True
        time.sleep(0.01)
    return until()


def test_setting_up_sends_a_test_email_then_turns_alerts_on(backend, keyring):
    from password_manager import prefs as prefsmod

    backend.setupEmailAlerts(f"  {ADDRESS} ", "abcd efgh ijkl mnop")
    assert settle(backend, lambda: backend.emailAlerts)
    [(address, password, message)] = backend.sent
    assert address == ADDRESS and message["To"] == ADDRESS and "Email alerts are on" in message["Subject"]
    assert keyring.store[(alerts.KEYRING_SERVICE, ADDRESS)] == "abcdefghijklmnop"
    assert backend.messages == [(f"Sent a test email to {ADDRESS}. Email alerts are on.", False)]
    saved = prefsmod.load()
    assert (saved.alert_email, saved.email_alerts) == (ADDRESS, True)
    assert not backend.emailBusy


def test_unsupported_address_sends_nothing(backend, keyring):
    backend.setupEmailAlerts("alex@example.com", "pw")
    assert backend.messages == [("Email alerts work with Gmail, iCloud Mail and Yahoo Mail addresses.", True)]
    assert backend.sent == [] and keyring.store == {} and not backend.emailAlerts


def test_lockout_sends_one_alert_per_ten_minutes(backend, keyring):
    from password_manager.vault import WrongMasterPassword

    backend.setupEmailAlerts(ADDRESS, "pw")
    assert settle(backend, lambda: backend.emailAlerts)
    backend._wrong(WrongMasterPassword(4, 0))   # not locked out yet: no alert
    backend._wrong(WrongMasterPassword(5, 30))
    backend._wrong(WrongMasterPassword(6, 60))  # within ten minutes of the last one: skipped
    assert settle(backend, lambda: len(backend.sent) >= 2)
    settle(backend, lambda: False)  # give a wrongly sent third alert time to show up
    subjects = [m["Subject"] for _a, _p, m in backend.sent]
    assert subjects == ["Password Manager: Email alerts are on",
                        "Password Manager: Wrong master password entered 5 times"]


def test_paused_or_removed_alerts_send_nothing(backend, keyring):
    backend.setupEmailAlerts(ADDRESS, "pw")
    assert settle(backend, lambda: backend.emailAlerts)
    backend.setEmailAlerts(False)
    backend._alert("password_changed")
    backend.setEmailAlerts(True)
    backend.removeEmailAlerts()
    backend._alert("password_changed")
    assert settle(backend, lambda: keyring.store == {})
    assert len(backend.sent) == 1 and backend.alertEmail == "" and not backend.emailAlerts
