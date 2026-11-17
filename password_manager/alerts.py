"""Security alert emails, sent from the user's own email account to that same address.

The account's app password lives in the system password store (macOS Keychain, Windows
Credential Manager, or the Secret Service on Linux), never in a file. An alert only ever
goes to the address it is sent from, and never contains anything from the vault: no
titles, user names or passwords.
"""

from __future__ import annotations

import html
import logging
import platform
import re
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

KEYRING_SERVICE = "Password Manager email alerts"
TIMEOUT = 20  # seconds for each step of talking to the mail server


class AlertError(Exception):
    """A problem to show the user, in plain words."""


@dataclass(frozen=True)
class Provider:
    name: str
    host: str
    port: int
    starttls: bool  # False = TLS from the first byte (port 465)
    help_url: str   # where to make an app password


GMAIL = Provider("Gmail", "smtp.gmail.com", 465, False, "https://myaccount.google.com/apppasswords")
ICLOUD = Provider("iCloud Mail", "smtp.mail.me.com", 587, True, "https://support.apple.com/en-us/102654")
YAHOO = Provider("Yahoo Mail", "smtp.mail.yahoo.com", 465, False, "https://help.yahoo.com/kb/SLN15241.html")
PROVIDERS = {"gmail.com": GMAIL, "googlemail.com": GMAIL, "icloud.com": ICLOUD, "me.com": ICLOUD,
             "mac.com": ICLOUD, "yahoo.com": YAHOO, "ymail.com": YAHOO}
_ADDRESS = re.compile(r"^[^@\s]+@([^@\s]+\.[^@\s]+)$")


def provider_for(address: str) -> Provider:
    match = _ADDRESS.match(address.strip())
    if not match:
        raise AlertError("Enter an email address like you@gmail.com.")
    provider = PROVIDERS.get(match.group(1).lower())
    if provider is None:
        raise AlertError("Email alerts work with Gmail, iCloud Mail and Yahoo Mail addresses.")
    return provider


def clean_app_password(password: str) -> str:
    """App passwords are shown in groups ("abcd efgh ijkl mnop"); the spaces aren't part of them."""
    return re.sub(r"\s+", "", password)


# ------------------------------------------------------------------ messages

def computer_name() -> str:
    name = platform.node() or "this computer"
    return name[:-6] if name.endswith(".local") else name


def _now() -> str:
    now = datetime.now().astimezone()
    return f"{now.day} {now:%B %Y, %H:%M} {now.tzname() or ''}".strip()


def _duration(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} seconds"
    minutes = round(seconds / 60)
    return "1 hour" if minutes >= 60 else f"{minutes} minute{'s' if minutes != 1 else ''}"


def describe(kind: str, **facts) -> Tuple[str, str, List[str]]:
    """(subject, headline, paragraphs) for one kind of alert."""
    where = facts.get("computer") or computer_name()
    if kind == "test":
        return ("Email alerts are on",
                "Email alerts are on",
                [f"This is a test from Password Manager on {where}. From now on, alerts about your "
                 "vault will arrive at this address.",
                 "You'll hear from it when someone is locked out after entering the wrong master password, "
                 "when the recovery key is used, when the master password or recovery key changes, and when "
                 "a leak check finds leaked passwords."])
    if kind == "lockout":
        attempts = facts.get("attempts", 0)
        return (f"Wrong master password entered {attempts} times",
                "Someone entered the wrong master password",
                [f"Password Manager on {where} has had {attempts} wrong master password or recovery key "
                 f"attempts in a row. It's blocking new attempts for {_duration(facts.get('locked_for', 0))}, "
                 "and the wait doubles with each further wrong attempt.",
                 "If this was you, you can ignore this email. If it wasn't, someone is trying to open your "
                 "vault on that computer: lock the computer, and once you're back in, change your master "
                 "password in Settings, Security."])
    if kind == "recovered":
        return ("Your vault was opened with the recovery key",
                "Your recovery key was used",
                [f"Someone used your recovery key on {where} to choose a new master password. "
                 "The old master password no longer works.",
                 "If this was you, make sure you kept the new recovery key the app showed you. If it wasn't, "
                 "someone has your recovery key: change the passwords stored in your vault, starting with "
                 "your email and bank accounts."])
    if kind == "password_changed":
        return ("Your master password was changed",
                "Your master password was changed",
                [f"The master password for your vault was changed on {where}.",
                 "If this was you, there's nothing else to do. If it wasn't, someone knew your old master "
                 "password: click \"Forgot password?\" on the lock screen, use your recovery key to take the "
                 "vault back, then change the passwords stored in it."])
    if kind == "recovery_key":
        return ("A new recovery key was made",
                "A new recovery key was made",
                [f"A new recovery key was made for your vault on {where}. The old one no longer works.",
                 "If this was you, keep the new key somewhere safe. If it wasn't, someone had your vault "
                 "open: change your master password in Settings, Security."])
    if kind == "leaks":
        count = facts.get("count", 0)
        plural = "s" if count != 1 else ""
        return (f"{count} of your passwords appeared in data leaks",
                f"{count} password{plural} found in data leaks",
                [f"A leak check on {where} found {count} of your saved password{plural} in Have I Been Pwned's "
                 "list of leaked passwords. Attackers try those first.",
                 "Open Password Manager and choose Leaked in the sidebar to see which ones, then change each "
                 "of them on its website."])
    raise ValueError(f"unknown alert: {kind}")


FOOTER = ("You're getting this because email alerts are on in Password Manager. Turn them off in "
          "Settings, Security. These emails never contain your passwords or the names of your accounts.")


# Inline styles: email apps ignore <style> blocks. The band's colour is the app icon's pink-to-purple.
_CSS = {
    "page": "margin:0;padding:24px 12px;background:#f3f0fa;"
            "font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif",
    "card": "max-width:560px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden",
    "band": "background:#211a52;background-image:linear-gradient(120deg,#2d2477,#15123a);padding:20px 24px",
    "icon": "display:block;width:56px;height:56px;border:0",
    "brand": "font-size:12px;font-weight:600;letter-spacing:1px;color:#c9c2ff",
    "headline": "font-size:20px;font-weight:700;color:#ffffff;margin-top:4px",
    "body": "padding:24px 28px 8px",
    "p": "margin:0 0 14px;font-size:15px;line-height:1.55;color:#2a2440",
    "facts": "margin:4px 0 18px;font-size:13px;color:#5d5675",
    "key": "padding:2px 14px 2px 0",
    "value": "color:#2a2440",
    "footer": "padding:14px 28px 22px;border-top:1px solid #ece8f5;font-size:12px;line-height:1.5;color:#8a83a0",
}


def compose(address: str, kind: str, **facts) -> EmailMessage:
    subject, headline, paragraphs = describe(kind, **facts)
    message = EmailMessage()
    message["Subject"] = f"Password Manager: {subject}"
    message["From"] = f"Password Manager <{address}>"
    message["To"] = address
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain="password-manager.local")
    when = _now()
    computer = facts.get("computer") or computer_name()
    message.set_content("\n\n".join([headline, *paragraphs, f"Computer: {computer}\nTime: {when}", FOOTER]) + "\n")
    esc = html.escape
    icon, icon_cid = _icon(), make_msgid(domain="password-manager.local")
    body = "".join(f'<p style="{_CSS["p"]}">{esc(p)}</p>' for p in paragraphs)
    rows = "".join(f'<tr><td style="{_CSS["key"]}">{k}</td><td style="{_CSS["value"]}">{esc(v)}</td></tr>'
                   for k, v in (("Computer", computer), ("Time", when)))
    message.add_alternative(
        f'<!doctype html><html><body style="{_CSS["page"]}">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="{_CSS["card"]}">'
        f'<tr><td style="{_CSS["band"]}"><table role="presentation" cellpadding="0" cellspacing="0"><tr>'
        + (f'<td style="padding-right:14px"><img src="cid:{icon_cid[1:-1]}" width="56" height="56" alt="" '
           f'style="{_CSS["icon"]}"></td>' if icon else "")
        + f'<td><div style="{_CSS["brand"]}">PASSWORD MANAGER</div>'
        f'<div style="{_CSS["headline"]}">{esc(headline)}</div></td></tr></table></td></tr>'
        f'<tr><td style="{_CSS["body"]}">{body}'
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="{_CSS["facts"]}">{rows}</table></td></tr>'
        f'<tr><td style="{_CSS["footer"]}">{esc(FOOTER)}</td></tr></table></body></html>\n',
        subtype="html")
    if icon:  # the app icon travels inside the email, so it shows without loading anything from the web
        message.get_body(("html",)).add_related(icon, maintype="image", subtype="png", cid=icon_cid,
                                                 disposition="inline", filename="password-manager.png")
    return message


def _icon() -> bytes:
    try:
        return (Path(__file__).resolve().parent / "assets" / "icon" / "app-128.png").read_bytes()
    except OSError:
        log.warning("The app icon is missing; sending the alert without it.")
        return b""


# ------------------------------------------------------------------- sending

def send(address: str, password: str, message: EmailMessage, smtp_factory: Optional[Callable] = None) -> None:
    """Send `message` through the account's own mail server. It must be addressed to that account."""
    if message["To"] != address or address not in message["From"]:
        raise AlertError("Alerts can only be sent to your own address.")
    provider = provider_for(address)
    context = tls_context()
    try:
        if smtp_factory is not None:
            server = smtp_factory(provider)
        elif provider.starttls:
            server = smtplib.SMTP(provider.host, provider.port, timeout=TIMEOUT)
        else:
            server = smtplib.SMTP_SSL(provider.host, provider.port, timeout=TIMEOUT, context=context)
        with server:
            if provider.starttls:
                server.starttls(context=context)
            server.login(address, clean_app_password(password))
            server.send_message(message, from_addr=address, to_addrs=[address])
    except AlertError:
        raise
    except smtplib.SMTPAuthenticationError as exc:
        log.warning("%s refused the sign-in: %s", provider.name, exc.smtp_code)
        raise AlertError(f"{provider.name} didn't accept that app password. Copy it again from your account "
                         "settings: it's a separate app password, not your normal password.") from exc
    except (ssl.SSLError, ssl.CertificateError) as exc:
        log.warning("TLS to %s failed: %s", provider.host, exc)
        raise AlertError(f"Couldn't make a secure connection to {provider.name}.") from exc
    except smtplib.SMTPException as exc:
        log.warning("%s refused the email: %s", provider.name, exc)
        raise AlertError(f"{provider.name} didn't send the email. Details are in the log.") from exc
    except OSError as exc:  # no network, DNS, timeouts, refused connections
        log.warning("Couldn't reach %s: %s", provider.host, exc)
        raise AlertError(f"Couldn't reach {provider.name}. Check your internet connection and try again.") from exc


def tls_context() -> ssl.SSLContext:
    from . import pwned  # the same bundled certificate list as the leak check

    return pwned.tls_context()


# -------------------------------------------------------- the password store

def _keyring():
    try:
        import keyring
    except ImportError as exc:  # pragma: no cover - keyring is a dependency
        raise AlertError("This copy of Password Manager can't use the system password store.") from exc
    return keyring


def save_password(address: str, password: str) -> None:
    try:
        _keyring().set_password(KEYRING_SERVICE, address, clean_app_password(password))
    except AlertError:
        raise
    except Exception as exc:  # noqa: BLE001 - each backend raises its own errors
        log.warning("Couldn't save the app password: %s", exc)
        raise AlertError("Couldn't save the app password in this computer's password store.") from exc


def load_password(address: str) -> str:
    try:
        password = _keyring().get_password(KEYRING_SERVICE, address)
    except AlertError:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("Couldn't read the app password: %s", exc)
        raise AlertError("Couldn't read the app password from this computer's password store.") from exc
    if not password:
        raise AlertError("The app password for email alerts is missing. Set up email alerts again.")
    return password


def forget_password(address: str) -> str:
    """Delete the stored app password: "removed", "missing" (nothing stored) or "failed"."""
    try:
        keyring = _keyring()
        if keyring.get_password(KEYRING_SERVICE, address) is None:
            return "missing"
        keyring.delete_password(KEYRING_SERVICE, address)
        return "removed"
    except Exception as exc:  # noqa: BLE001 - each password store raises its own errors
        log.warning("Couldn't remove the app password: %s", exc)
        return "failed"


class Throttle:
    """At most one alert of each kind per `seconds`, so a stream of events doesn't flood the inbox."""

    def __init__(self, seconds: float, clock: Callable[[], float]) -> None:
        self.seconds = seconds
        self.clock = clock
        self._last: Dict[str, float] = {}

    def allow(self, kind: str) -> bool:
        now = self.clock()
        last = self._last.get(kind)
        if last is not None and now - last < self.seconds:
            return False
        self._last[kind] = now
        return True
