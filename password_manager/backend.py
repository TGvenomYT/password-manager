"""Bridge between the QML interface and the vault.

All vault and database work runs on one background thread, so the interface keeps animating
while scrypt or MySQL is busy. Results come back to the GUI thread through a Qt signal.
"""

from __future__ import annotations

import logging
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import mysql.connector
from PySide6.QtCore import QEvent, QObject, QTimer, QUrl, Property, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

from . import alerts, audit, backup, csvio, credentials, crypto, db, generator, pwned, totp
from . import config as cfgmod
from . import prefs as prefsmod
from .vault import (
    FREE_ATTEMPTS, MIN_MASTER_PASSWORD_LENGTH, TRASH_DAYS, Entry, NoRecoveryKey, Vault, VaultError, VaultLocked,
    WrongMasterPassword, WrongRecoveryKey, site_host,
)

log = logging.getLogger(__name__)

AVATAR_COLORS = ["#4C8DFF", "#2EC5D3", "#34C77B", "#7B6CFF", "#FF9F43", "#FF4F8B", "#B45CFF",
                 "#FF5C5C", "#C08B5C", "#19C2A6", "#5F6BFF", "#F2711C"]
VIEW_TITLES = {"all": "All Passwords", "favorites": "Favorites", "codes": "Verification Codes",
               "notes": "Secure Notes", "security": "Security", "weak": "Weak Passwords",
               "reused": "Reused Passwords", "old": "Old Passwords", "pwned": "Leaked Passwords",
               "trash": "Recently Deleted"}
OLD_DAYS = 365  # a password unchanged for longer than this is "old"
INTROS = {
    "created": "Your vault is ready. If you ever forget your master password, this key is the only way back in.",
    "missing": "Your vault doesn't have a recovery key yet. If you forget your master password, this key is "
               "the only way back in.",
    "recovered": "Your master password has been changed. Save this new recovery key; the old one keeps "
                 "working until you do.",
    "replace": "This new key replaces your old recovery key once you save it.",
}


def avatar_color(name: str) -> str:
    return AVATAR_COLORS[sum(ord(c) * (i + 7) for i, c in enumerate(name.lower())) % len(AVATAR_COLORS)]


def _when(timestamp: float) -> str:
    if not timestamp:
        return "unknown"
    moment = datetime.fromtimestamp(timestamp)
    return f"{moment.day} {moment:%b %Y} at {moment:%H:%M}"


def _local_path(url) -> str:
    return QUrl(url).toLocalFile() if isinstance(url, str) and url.startswith("file:") else str(url)


class Backend(QObject):
    stageChanged = Signal()
    busyChanged = Signal()
    errorChanged = Signal()
    lockoutChanged = Signal()
    listChanged = Signal()
    selectedChanged = Signal()
    recoveryChanged = Signal()
    prefsChanged = Signal()
    toast = Signal(str, arguments=["message"])
    shake = Signal()
    entrySaved = Signal(int, arguments=["entryId"])
    editorError = Signal(str, arguments=["message"])
    dialogMessage = Signal(str, bool, arguments=["message", "isError"])
    passwordChanged = Signal()
    undoable = Signal(str, arguments=["message"])
    securityChanged = Signal()
    alertsChanged = Signal()
    _done = Signal(object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vault")
        self._mail_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mail")  # never holds up the vault
        self._mail_busy = False
        self._alert_throttle = alerts.Throttle(600, time.monotonic)
        self._done.connect(self._finish)
        self._busy = 0
        self._stage = "loading"
        self._error = ""
        self._fatal = ""
        self._cfg = None
        self._gpg = ""
        self._conn = None
        self.vault: Optional[Vault] = None
        self.prefs = prefsmod.load()
        self._lockout_until = 0.0
        self._recovery_key = ""
        self._recovery_reason = "created"
        self._after_recovery: Callable[[], None] = self._enter_main
        self._active: List[Entry] = []
        self._deleted: List[Entry] = []
        self._reuse: Dict[int, List[int]] = {}
        self._weak: set = set()
        self._view = "all"
        self._query = ""
        self._selected_id = -1
        self._items: list = []
        self._selected_map: dict = {}
        self._secret: Optional[str] = None
        self._last_activity = time.monotonic()
        self._pwned: Dict[int, int] = {}
        self._checked_at = 0.0
        self._checking = False
        self._undo: Optional[Callable[[], None]] = None

        self._tick = QTimer(self, interval=1000)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start()
        self._clip_timer = QTimer(self, singleShot=True)
        self._clip_timer.timeout.connect(self._clear_clipboard)
        app = QGuiApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            app.aboutToQuit.connect(self.shutdown)

    # ------------------------------------------------------------- threading

    def _run(self, work: Callable, done: Callable = None, failed: Callable = None) -> None:
        self._busy += 1
        self.busyChanged.emit()
        future = self._pool.submit(work)
        future.add_done_callback(lambda f: self._done.emit((f, done, failed, True)))

    def _run_mail(self, work: Callable, done: Callable = None, failed: Callable = None) -> None:
        future = self._mail_pool.submit(work)
        future.add_done_callback(lambda f: self._done.emit((f, done, failed, False)))

    def _finish(self, payload) -> None:
        future, done, failed, counted = payload
        if counted:
            self._busy -= 1
            self.busyChanged.emit()
        try:
            result = future.result()
        except Exception as exc:  # noqa: BLE001 - every error is shown to the user somewhere
            if failed is not None:
                failed(exc)
            else:
                log.exception("Background task failed", exc_info=exc)
                self.toast.emit(f"Something went wrong: {exc}")
            return
        if done is not None:
            done(result)

    # ------------------------------------------------------------ properties

    def _get_stage(self) -> str:
        return self._stage

    stage = Property(str, _get_stage, notify=stageChanged)

    def _set_stage(self, stage: str) -> None:
        self._stage = stage
        self._set_error("")
        self.stageChanged.emit()

    def _get_busy(self) -> bool:
        return self._busy > 0

    busy = Property(bool, _get_busy, notify=busyChanged)

    def _get_error(self) -> str:
        return self._error

    error = Property(str, _get_error, notify=errorChanged)

    def _set_error(self, text: str) -> None:
        if text != self._error:
            self._error = text
            self.errorChanged.emit()

    def _get_fatal(self) -> str:
        return self._fatal

    fatal = Property(str, _get_fatal, notify=stageChanged)

    def _get_lockout(self) -> int:
        return max(0, int(self._lockout_until - time.monotonic() + 0.999))

    lockoutSeconds = Property(int, _get_lockout, notify=lockoutChanged)

    def _get_min_length(self) -> int:
        return MIN_MASTER_PASSWORD_LENGTH

    minPasswordLength = Property(int, _get_min_length, constant=True)

    def _get_recovery_key(self) -> str:
        return self._recovery_key

    recoveryKey = Property(str, _get_recovery_key, notify=recoveryChanged)

    def _get_recovery_intro(self) -> str:
        return INTROS.get(self._recovery_reason, "")

    recoveryIntro = Property(str, _get_recovery_intro, notify=recoveryChanged)

    def _get_view(self) -> str:
        return self._view

    view = Property(str, _get_view, notify=listChanged)

    def _get_view_title(self) -> str:
        return VIEW_TITLES[self._view]

    viewTitle = Property(str, _get_view_title, notify=listChanged)

    def _get_query(self) -> str:
        return self._query

    query = Property(str, _get_query, notify=listChanged)

    def _get_items(self) -> list:
        return self._items

    items = Property("QVariantList", _get_items, notify=listChanged)

    def _get_counts(self) -> dict:
        return {"all": len(self._active), "favorites": sum(e.favorite for e in self._active),
                "codes": sum(1 for e in self._active if e.totp),
                "notes": sum(1 for e in self._active if e.kind == "note"),
                "weak": len(self._weak), "reused": len(self._reuse),
                "old": sum(1 for e in self._active if self._is_old(e)),
                "pwned": sum(1 for count in self._pwned.values() if count > 0), "trash": len(self._deleted)}

    counts = Property("QVariantMap", _get_counts, notify=listChanged)

    def _get_selected_id(self) -> int:
        return self._selected_id

    selectedId = Property(int, _get_selected_id, notify=selectedChanged)

    def _get_selected(self) -> dict:
        return self._selected_map

    def _update_selected(self) -> None:
        self._selected_map = self._describe(self._entry(self._selected_id))
        self.selectedChanged.emit()

    def _describe(self, entry: Optional[Entry]) -> dict:
        if entry is None:
            return {}
        score = audit.strength(entry.password) if entry.password else 0
        others = self._reuse.get(entry.id, []) if entry.deleted_at is None else []
        days_left = (max(0, TRASH_DAYS - int((time.time() - entry.deleted_at) // 86400))
                     if entry.deleted_at is not None else 0)
        return {
            "id": entry.id, "name": entry.name, "title": entry.title, "website": entry.website,
            "host": site_host(entry.website), "username": entry.username,
            "hasPassword": bool(entry.password), "decryptable": entry.password is not None,
            "notes": entry.notes, "favorite": entry.favorite, "deleted": entry.deleted_at is not None,
            "daysLeft": days_left, "strength": score, "strengthLabel": audit.LABELS[score],
            "weak": entry.deleted_at is None and entry.id in self._weak,
            "reusedWith": [self._name_of(i) for i in others],
            "created": _when(entry.created_at), "modified": _when(entry.updated_at),
            "color": avatar_color(entry.name), "initial": self._initial(entry.name),
            "kind": entry.kind, "totp": entry.totp, "hasTotp": bool(entry.totp),
            "history": [{"changed": _when(h.get("changed", 0))} for h in entry.history],
            "old": entry.deleted_at is None and self._is_old(entry),
            "ageDays": int((time.time() - (entry.updated_at or entry.created_at or time.time())) // 86400),
            "pwned": self._pwned.get(entry.id, 0),
        }

    selected = Property("QVariantMap", _get_selected, notify=selectedChanged)

    def _get_checking(self) -> bool:
        return self._checking

    checking = Property(bool, _get_checking, notify=securityChanged)

    def _get_security(self) -> dict:
        logins = [e for e in self._active if e.kind == "login" and e.password]
        penalty = 0.0
        for e in logins:
            if self._pwned.get(e.id, 0) > 0 or e.id in self._weak:
                penalty += 1.0
            elif e.id in self._reuse:
                penalty += 0.7
            elif self._is_old(e):
                penalty += 0.3
        score = 100 if not logins else round(100 * (1 - penalty / len(logins)))
        return {"score": score, "logins": len(logins), "weak": len(self._weak), "reused": len(self._reuse),
                "old": sum(1 for e in logins if self._is_old(e)),
                "pwned": sum(1 for count in self._pwned.values() if count > 0),
                "codes": sum(1 for e in logins if e.totp), "checked": self._checked_at > 0,
                "checkedAt": _when(self._checked_at) if self._checked_at else ""}

    security = Property("QVariantMap", _get_security, notify=securityChanged)

    def _get_theme(self) -> str:
        return self.prefs.theme

    theme = Property(str, _get_theme, notify=prefsChanged)

    def _get_sort(self) -> str:
        return self.prefs.sort

    sort = Property(str, _get_sort, notify=prefsChanged)

    def _get_auto_lock(self) -> int:
        return self.prefs.auto_lock_minutes

    autoLockMinutes = Property(int, _get_auto_lock, notify=prefsChanged)

    def _get_clip_seconds(self) -> int:
        return self.prefs.clipboard_seconds

    clipboardSeconds = Property(int, _get_clip_seconds, notify=prefsChanged)

    def _get_reduce_motion(self) -> bool:
        return self.prefs.reduce_motion

    reduceMotion = Property(bool, _get_reduce_motion, notify=prefsChanged)

    def _get_generator(self) -> dict:
        p = self.prefs
        return {"style": p.generator_style, "length": p.generator_length, "digits": p.generator_digits,
                "symbols": p.generator_symbols}

    generatorOptions = Property("QVariantMap", _get_generator, notify=prefsChanged)

    def _get_alert_email(self) -> str:
        return self.prefs.alert_email

    alertEmail = Property(str, _get_alert_email, notify=alertsChanged)

    def _get_email_alerts(self) -> bool:
        return self.prefs.email_alerts and bool(self.prefs.alert_email)

    emailAlerts = Property(bool, _get_email_alerts, notify=alertsChanged)

    def _get_email_busy(self) -> bool:
        return self._mail_busy

    emailBusy = Property(bool, _get_email_busy, notify=alertsChanged)

    # ----------------------------------------------------------------- startup

    def start(self) -> None:
        """Find the settings and the database login, using gpg-agent's cache when it has one."""
        def work():
            cfg = cfgmod.load()
            gpg = credentials.find_gpg(cfg.gpg_binary)
            path = cfg.credential_path()
            if not path.is_file():
                raise credentials.GpgError(f"The database credential file is missing: {path}")
            return cfg, gpg, credentials.decrypt_cached(path, gpg)

        def done(result):
            self._cfg, self._gpg, password = result
            if password is None:
                self._set_stage("gpg")
            else:
                self._connect(password)

        self._run(work, done, self._startup_failed)

    def _startup_failed(self, exc: Exception) -> None:
        if isinstance(exc, cfgmod.ConfigError):
            message = f"{exc}\n\nRun the installer again, or run:  python -m password_manager setup"
        elif isinstance(exc, credentials.GpgError):
            message = f"Couldn't decrypt the database login.\n\n{exc}"
        elif isinstance(exc, mysql.connector.Error):
            user = self._cfg.db.user if self._cfg else "the app user"
            message = (f"Couldn't connect to MySQL as '{user}'.\n\n{exc}\n\nMake sure the MySQL server is running "
                       "(macOS: brew services start mysql, Linux: sudo systemctl start mysql, "
                       "Windows: Services, then MySQL).")
        else:
            message = f"Couldn't open the vault.\n\n{exc}"
        log.error(message)
        self._fatal = message
        self._set_stage("fatal")

    @Slot(str)
    def submitGpg(self, passphrase: str) -> None:
        if not passphrase:
            self._set_error("Enter your GPG passphrase.")
            return

        def work():
            return credentials.decrypt_with_passphrase(self._cfg.credential_path(), passphrase, self._gpg)

        def failed(exc):
            if isinstance(exc, credentials.BadPassphrase):
                self._set_error("That GPG passphrase is wrong. Try again.")
                self.shake.emit()
            else:
                self._startup_failed(exc)

        self._run(work, self._connect, failed)

    def _connect(self, db_password: str) -> None:
        def work():
            conn = db.connect(self._cfg.db, db_password)
            vault = Vault(conn)
            try:
                vault.ensure_schema()
                return conn, vault, vault.needs_master_password_setup(), vault.lockout_remaining()
            except BaseException:
                conn.close()
                raise

        def done(result):
            self._conn, self.vault, needs_setup, lockout = result
            self._set_lockout(lockout)
            self._set_stage("create" if needs_setup else "unlock")

        self._run(work, done, self._startup_failed)

    def attach(self, vault: Vault, conn=None, needs_setup: bool = False) -> None:
        """Use an already-open vault (tests and tools)."""
        self.vault, self._conn = vault, conn
        self._set_stage("create" if needs_setup else "unlock")

    # ------------------------------------------------------------ lock screens

    def _set_lockout(self, seconds: float) -> None:
        self._lockout_until = time.monotonic() + seconds if seconds > 0 else 0.0
        self.lockoutChanged.emit()

    def _wrong(self, exc: WrongMasterPassword) -> None:
        if exc.locked_for:
            self._alert("lockout", attempts=exc.failed_attempts, locked_for=exc.locked_for)
            self._set_lockout(exc.locked_for)
            self._set_error("")
        else:
            left = FREE_ATTEMPTS - exc.failed_attempts
            self._set_error(f"{exc} {left} attempt{'s' if left != 1 else ''} left before a short lockout.")
        self.shake.emit()

    def _lock_failure(self, exc: Exception) -> None:
        if isinstance(exc, WrongMasterPassword):
            self._wrong(exc)
        elif isinstance(exc, VaultLocked):
            self._set_lockout(exc.remaining)
            self.shake.emit()
        elif isinstance(exc, (VaultError, mysql.connector.Error)):
            self._set_error(str(exc))
            self.shake.emit()
        else:
            raise exc

    @Slot(str)
    def unlock(self, password: str) -> None:
        if not password:
            self._set_error("Enter your master password.")
            self.shake.emit()
            return
        self._run(lambda: (self.vault.unlock(password), self.vault.has_recovery_key())[1],
                  self._after_unlock, self._lock_failure)

    def _after_unlock(self, has_key: bool) -> None:
        if has_key:
            self._enter_main()
        else:
            self._show_recovery_key("missing", self._enter_main)

    @Slot(str, str)
    def createVault(self, password: str, confirm: str) -> None:
        if password != confirm:
            self._set_error("The passwords don't match.")
            self.shake.emit()
            return
        self._run(lambda: self.vault.create(password),
                  lambda _r: self._show_recovery_key("created", self._enter_main), self._lock_failure)

    @Slot()
    def forgotPassword(self) -> None:
        self._run(self.vault.has_recovery_key, lambda has: self._set_stage("recover" if has else "noRecovery"),
                  self._lock_failure)

    @Slot()
    def backToUnlock(self) -> None:
        self._set_stage("unlock")

    @Slot(str, str, str)
    def recover(self, key: str, password: str, confirm: str) -> None:
        if password != confirm:
            self._set_error("The new passwords don't match.")
            self.shake.emit()
            return

        def failed(exc):
            if isinstance(exc, WrongRecoveryKey):
                self._wrong(exc)
            elif isinstance(exc, NoRecoveryKey):
                self._set_stage("noRecovery")
            else:
                self._lock_failure(exc)

        def done(_r):
            self._alert("recovered")
            self._show_recovery_key("recovered", self._enter_main)

        self._run(lambda: self.vault.recover(key, password), done, failed)

    def _show_recovery_key(self, reason: str, then: Callable[[], None]) -> None:
        self._recovery_key = crypto.new_recovery_key()
        self._recovery_reason = reason
        self._after_recovery = then
        self.recoveryChanged.emit()
        self._set_stage("recoveryKey")

    @Slot()
    def saveRecoveryKey(self) -> None:
        key, reason = self._recovery_key, self._recovery_reason

        def done(_r):
            if reason == "replace":
                self._alert("recovery_key")
            self._after_recovery()

        self._run(lambda: self.vault.set_recovery_key(key), done,
                  lambda exc: self._set_error(f"Couldn't store the recovery key: {exc}"))

    @Slot()
    def skipRecoveryKey(self) -> None:
        self._after_recovery()

    @Slot()
    def copyRecoveryKey(self) -> None:
        self._copy(self._recovery_key, secret=False)
        self.toast.emit("Recovery key copied. Paste it somewhere safe.")

    @Slot(str)
    def saveRecoveryKeyFile(self, url: str) -> None:
        path = _local_path(url)
        try:
            Path(path).write_text(
                f"Password Manager recovery key\nCreated {date.today().isoformat()}\n\n{self._recovery_key}\n\n"
                "If you forget your master password, click \"Forgot password?\" on the lock screen\n"
                "and enter this key to choose a new one. Keep it private: together with access to\n"
                "your database, it opens your vault.\n", encoding="utf-8")
        except OSError as exc:
            self._set_error(f"Couldn't save the file: {exc}")
            return
        self.toast.emit(f"Saved to {path}")

    @Slot()
    def lock(self) -> None:
        if self.vault is None or self._stage in ("loading", "gpg", "fatal"):
            return
        self._clear_clipboard()
        self.vault.lock()
        self._active, self._deleted, self._items = [], [], []
        self._pwned, self._checked_at, self._undo = {}, 0.0, None
        self._selected_id = -1
        self.listChanged.emit()
        self._update_selected()
        self._set_stage("unlock")

    # ------------------------------------------------------------ main window

    def _enter_main(self) -> None:
        self._view, self._query = "all", ""
        self._set_stage("main")
        self.reload()

    def reload(self, select: int = -1) -> None:
        def work():
            return self.vault.entries(), self.vault.entries(trash=True)

        def done(result):
            self._active, self._deleted = result
            self._reuse = audit.reused(self._active)
            self._weak = {e.id for e in self._active if e.password and audit.is_weak(e.password)}
            self._refresh(select)

        self._run(work, done, lambda exc: self.toast.emit(f"Couldn't load your passwords: {exc}"))

    def _visible(self) -> List[Entry]:
        source = self._deleted if self._view == "trash" else self._active
        if self._view == "favorites":
            source = [e for e in source if e.favorite]
        elif self._view == "weak":
            source = [e for e in source if e.id in self._weak]
        elif self._view == "reused":
            source = [e for e in source if e.id in self._reuse]
        elif self._view == "codes":
            source = [e for e in source if e.totp]
        elif self._view == "notes":
            source = [e for e in source if e.kind == "note"]
        elif self._view == "old":
            source = [e for e in source if self._is_old(e)]
        elif self._view == "pwned":
            source = [e for e in source if self._pwned.get(e.id, 0) > 0]
        elif self._view == "security":
            source = []
        if self.prefs.sort == "modified":
            source = sorted(source, key=lambda e: -(e.updated_at or 0))
        elif self.prefs.sort == "created":
            source = sorted(source, key=lambda e: -(e.created_at or 0))
        q = self._query.strip().lower()
        if q:
            source = [e for e in source if q in e.name.lower() or q in e.username.lower()
                      or q in e.website.lower() or q in e.notes.lower()]
        return source

    def _refresh(self, select: int = -1) -> None:
        visible = self._visible()
        ids = [e.id for e in visible]
        if select in ids:
            self._selected_id = select
        elif self._selected_id not in ids:
            self._selected_id = ids[0] if ids else -1
        self._items = [{
            "id": e.id, "name": e.name, "initial": self._initial(e.name), "color": avatar_color(e.name),
            "subtitle": (e.username if e.username and e.username != e.name else "") or site_host(e.website)
            or e.username or "No user name",
            "favorite": e.favorite, "weak": e.id in self._weak, "reused": e.id in self._reuse,
            "kind": e.kind, "hasTotp": bool(e.totp), "pwned": self._pwned.get(e.id, 0) > 0,
        } for e in visible]
        self.listChanged.emit()
        self.securityChanged.emit()
        self._update_selected()

    @staticmethod
    def _is_old(entry: Entry) -> bool:
        changed = entry.updated_at or entry.created_at
        return entry.kind == "login" and bool(entry.password) and bool(changed) and \
            time.time() - changed > OLD_DAYS * 86400

    @staticmethod
    def _initial(name: str) -> str:
        return next((c for c in name if c.isalnum()), "?").upper()

    def _entry(self, entry_id: int) -> Optional[Entry]:
        return next((e for e in self._active + self._deleted if e.id == entry_id), None)

    def _name_of(self, entry_id: int) -> str:
        entry = self._entry(entry_id)
        return entry.name if entry else "another entry"

    @Slot(str)
    def setView(self, view: str) -> None:
        if view in VIEW_TITLES and view != self._view:
            self._view = view
            self._selected_id = -1
            self._refresh()

    @Slot(str)
    def setQuery(self, query: str) -> None:
        if query != self._query:
            self._query = query
            self._refresh()

    @Slot(int)
    def select(self, entry_id: int) -> None:
        if entry_id != self._selected_id:
            self._selected_id = entry_id
            self._update_selected()

    @Slot(str)
    def copyField(self, field: str) -> None:
        entry = self._entry(self._selected_id)
        if entry is None:
            return
        if field == "totp":
            try:
                value = totp.parse(entry.totp).code() if entry.totp else ""
            except ValueError:
                value = ""
        else:
            value = getattr(entry, field, "") or ""
        if not value:
            return
        secret = field in ("password", "notes", "totp")
        seconds = self._copy(value, secret)
        label = {"password": "Password", "username": "User name", "website": "Website", "notes": "Notes",
                 "totp": "Verification code"}[field]
        self.toast.emit(f"{label} copied" + (f" · clears in {seconds} s" if seconds else ""))

    @Slot(int, result=str)
    def passwordFor(self, entry_id: int) -> str:
        """The saved password, only to fill the (masked) editor field. Nothing else in the interface
        receives a password: the details view copies it straight from here to the clipboard."""
        entry = self._entry(entry_id)
        return (entry.password or "") if entry is not None else ""

    @Slot(str)
    def copyPassword(self, text: str) -> None:
        """Copy a password the editor holds (typed or generated) without showing it."""
        if not text:
            return
        seconds = self._copy(text, True)
        self.toast.emit("Password copied" + (f" \u00b7 clears in {seconds} s" if seconds else ""))

    @Slot(int)
    def copyHistory(self, index: int) -> None:
        entry = self._entry(self._selected_id)
        if entry is not None and 0 <= index < len(entry.history):
            seconds = self._copy(entry.history[index]["password"], True)
            self.toast.emit("Earlier password copied" + (f" \u00b7 clears in {seconds} s" if seconds else ""))

    @Slot(result="QVariantMap")
    def currentCode(self) -> dict:
        """The selected entry's live 2FA code: {code, remaining, period}, or {} if it has none."""
        entry = self._entry(self._selected_id)
        if entry is None or not entry.totp:
            return {}
        try:
            spec = totp.parse(entry.totp)
        except ValueError:
            return {"code": "", "remaining": 0, "period": 30, "error": "Invalid 2FA key"}
        return {"code": spec.code(), "remaining": spec.remaining(), "period": spec.period}

    @Slot(str, result="QVariantMap")
    def totpPreview(self, text: str) -> dict:
        if not text.strip():
            return {"valid": False, "code": "", "error": ""}
        try:
            spec = totp.parse(text)
        except ValueError as exc:
            return {"valid": False, "code": "", "error": str(exc)}
        return {"valid": True, "code": spec.code(), "error": "", "issuer": spec.issuer}

    def _copy(self, text: str, secret: bool) -> int:
        QGuiApplication.clipboard().setText(text)
        seconds = self.prefs.clipboard_seconds if secret else 0
        self._secret = text if secret else None
        self._clip_timer.stop()
        if seconds > 0:
            self._clip_timer.start(seconds * 1000)
        return seconds

    def _clear_clipboard(self) -> None:
        if self._secret is not None and QGuiApplication.clipboard().text() == self._secret:
            QGuiApplication.clipboard().clear()
        self._secret = None

    @Slot(str)
    def openWebsite(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url if "://" in url else "https://" + url))

    def _mutate(self, work: Callable, message: str = "", select: int = -1) -> None:
        def done(_result):
            if message:
                self.toast.emit(message)
            self.reload(select)
        self._run(work, done, lambda exc: self.toast.emit(f"Couldn't do that: {exc}"))

    @Slot()
    def toggleFavorite(self) -> None:
        entry = self._entry(self._selected_id)
        if entry is not None and entry.deleted_at is None:
            self._mutate(lambda: self.vault.set_favorite(entry.id, not entry.favorite), select=entry.id)

    @Slot()
    def trashSelected(self) -> None:
        entry = self._entry(self._selected_id)
        if entry is None or entry.deleted_at is not None:
            return

        def done(_r):
            self._undo = lambda: self._mutate(lambda: self.vault.restore_entry(entry.id),
                                              f"“{entry.name}” restored", select=entry.id)
            self.undoable.emit(f"“{entry.name}” moved to Recently Deleted")
            self.reload()

        self._run(lambda: self.vault.trash_entry(entry.id), done,
                  lambda exc: self.toast.emit(f"Couldn't do that: {exc}"))

    @Slot()
    def undo(self) -> None:
        action, self._undo = self._undo, None
        if action is not None:
            action()

    @Slot()
    def restoreSelected(self) -> None:
        entry = self._entry(self._selected_id)
        if entry is not None and entry.deleted_at is not None:
            self._mutate(lambda: self.vault.restore_entry(entry.id), f"“{entry.name}” restored")

    @Slot()
    def deleteSelectedNow(self) -> None:
        entry = self._entry(self._selected_id)
        if entry is not None:
            self._mutate(lambda: self.vault.delete_entry(entry.id), f"“{entry.name}” deleted")

    @Slot()
    def emptyTrash(self) -> None:
        self._mutate(self.vault.empty_trash, "Recently Deleted emptied")

    @Slot(int, str, str, str, str, str, str, str)
    def saveEntry(self, entry_id: int, kind: str, title: str, website: str, username: str, password: str,
                  secret: str, notes: str) -> None:
        if kind == "note":
            website = username = secret = ""

        def work():
            if entry_id < 0:
                return self.vault.add_entry(username, password, title=title, website=website, notes=notes,
                                            totp=secret, kind=kind)
            self.vault.update_entry(entry_id, title=title, username=username, password=password,
                                    website=website, notes=notes, totp=secret, kind=kind)
            return entry_id

        def done(new_id):
            if self._view not in ("all", "favorites", "codes", "notes"):
                self._view = "all"
            self._query = ""
            self.entrySaved.emit(new_id)
            self.toast.emit("Saved")
            self.reload(new_id)

        def failed(exc):
            self.editorError.emit(str(exc) if isinstance(exc, ValueError) else f"Couldn't save: {exc}")

        self._run(work, done, failed)

    # ---------------------------------------------------------------- tools

    @Slot(str, int, bool, bool, result=str)
    def generatePassword(self, style: str, length: int, digits: bool, symbols: bool) -> str:
        p = self.prefs
        p.generator_style, p.generator_length = style, int(length)
        p.generator_digits, p.generator_symbols = bool(digits), bool(symbols)
        prefsmod.save(p)
        if style == "memorable":
            return generator.memorable_password()
        return generator.random_password(length, digits=digits, symbols=symbols)

    @Slot(str, result=int)
    def strength(self, password: str) -> int:
        return audit.strength(password) if password else -1

    @Slot(int, result=str)
    def strengthLabel(self, score: int) -> str:
        return audit.LABELS[score] if 0 <= score < len(audit.LABELS) else ""

    # ------------------------------------------------------------ security

    @Slot()
    def checkLeaks(self) -> None:
        """Ask Have I Been Pwned about every password; only 5-character hash prefixes are sent."""
        if self._checking:
            return
        entries = [e for e in self._active if e.password]
        self._checking = True
        self.securityChanged.emit()

        def done(counts):
            self._checking = False
            self._checked_at = time.time()
            self._pwned = {e.id: counts.get(e.password, 0) for e in entries}
            leaked = sum(1 for n in self._pwned.values() if n > 0)
            self.toast.emit("None of your passwords appear in known leaks" if not leaked else
                            f"{leaked} password{'s' if leaked != 1 else ''} appeared in data leaks")
            if leaked:
                self._alert("leaks", count=leaked)
            self._refresh(self._selected_id)

        def failed(exc):
            self._checking = False
            self.securityChanged.emit()
            log.warning("Leak check failed: %s", exc)
            if "CERTIFICATE" in str(exc).upper() or isinstance(getattr(exc, "reason", None), ssl.SSLError):
                self.toast.emit("Couldn't verify the secure connection to Have I Been Pwned.")
            elif isinstance(exc, OSError):  # URLError, timeouts, no network
                self.toast.emit("Couldn't reach Have I Been Pwned. Check your internet connection and try again.")
            else:
                self.toast.emit("The leak check didn't finish. Details are in the log.")

        self._run(lambda: pwned.check(e.password for e in entries), done, failed)

    @Slot(str, result="QVariantList")
    def search(self, query: str) -> list:
        """Entries matching `query`, for the command palette."""
        q = query.strip().lower()
        found = [e for e in self._active if not q or q in e.name.lower() or q in e.username.lower()
                 or q in e.website.lower()]
        return [{"id": e.id, "name": e.name, "subtitle": e.username or site_host(e.website) or "",
                 "initial": self._initial(e.name), "color": avatar_color(e.name)} for e in found[:8]]

    @Slot(int)
    def reveal(self, entry_id: int) -> None:
        """Show an entry from anywhere (the command palette)."""
        self._view, self._query = "all", ""
        self._selected_id = entry_id
        self._refresh(entry_id)

    @Slot(str)
    def setTheme(self, name: str) -> None:
        if name in ("aurora", "ocean", "sunset", "forest"):
            self.prefs.theme = name
            prefsmod.save(self.prefs)
            self.prefsChanged.emit()

    @Slot(str)
    def setSort(self, key: str) -> None:
        if key in ("name", "modified", "created"):
            self.prefs.sort = key
            prefsmod.save(self.prefs)
            self.prefsChanged.emit()
            self._refresh(self._selected_id)

    @Slot(str, str, str)
    def exportBackup(self, url: str, password: str, confirm: str) -> None:
        if password != confirm:
            self.dialogMessage.emit("The backup passwords don't match.", True)
            return
        path = _local_path(url)

        def done(count):
            self.dialogMessage.emit(f"Backed up {count} item{'s' if count != 1 else ''} to {path}.", False)

        def failed(exc):
            self.dialogMessage.emit(str(exc) if isinstance(exc, ValueError) else f"Couldn't back up: {exc}", True)

        self._run(lambda: backup.write(path, self.vault.entries(), password), done, failed)

    @Slot(str, str)
    def importBackup(self, url: str, password: str) -> None:
        path = _local_path(url)

        def work():
            return self.vault.import_entries(backup.read(path, password))

        def done(result):
            added, skipped = result
            self.dialogMessage.emit(f"Restored {added} item{'s' if added != 1 else ''}."
                                    + (f" Skipped {skipped} you already have." if skipped else ""), False)
            self.reload()

        def failed(exc):
            self.dialogMessage.emit(str(exc) if isinstance(exc, ValueError) else f"Couldn't restore: {exc}", True)

        self._run(work, done, failed)

    # ---------------------------------------------------------------- settings

    @Slot(int)
    def setAutoLock(self, minutes: int) -> None:
        self.prefs.auto_lock_minutes = int(minutes)
        prefsmod.save(self.prefs)
        self.prefsChanged.emit()

    @Slot(int)
    def setClipboardSeconds(self, seconds: int) -> None:
        self.prefs.clipboard_seconds = int(seconds)
        prefsmod.save(self.prefs)
        self.prefsChanged.emit()

    @Slot(bool)
    def setReduceMotion(self, on: bool) -> None:
        self.prefs.reduce_motion = bool(on)
        prefsmod.save(self.prefs)
        self.prefsChanged.emit()

    @Slot(str, str, str)
    def changeMasterPassword(self, current: str, new: str, confirm: str) -> None:
        if new != confirm:
            self.dialogMessage.emit("The new passwords don't match.", True)
            return

        def done(_r):
            self.passwordChanged.emit()
            self.toast.emit("Master password changed")
            self._alert("password_changed")

        def failed(exc):
            if isinstance(exc, WrongMasterPassword):
                if exc.locked_for:
                    self._alert("lockout", attempts=exc.failed_attempts, locked_for=exc.locked_for)
                left = FREE_ATTEMPTS - exc.failed_attempts
                tail = f" {left} attempt{'s' if left != 1 else ''} left before a short lockout." if left > 0 else ""
                self.dialogMessage.emit("Wrong current password." + tail, True)
            elif isinstance(exc, (VaultError, mysql.connector.Error)):
                self.dialogMessage.emit(str(exc), True)
            else:
                raise exc

        self._run(lambda: self.vault.change_master_password(current, new), done, failed)

    @Slot()
    def newRecoveryKey(self) -> None:
        self._show_recovery_key("replace", lambda: (self._set_stage("main"), self.reload(self._selected_id)))

    # ---------------------------------------------------------- email alerts

    def _set_mail_busy(self, busy: bool) -> None:
        self._mail_busy = busy
        self.alertsChanged.emit()

    @Slot(str, result=str)
    def appPasswordHelp(self, address: str) -> str:
        """Where to make an app password for this address ("" if it isn't a supported one)."""
        try:
            return alerts.provider_for(address).help_url
        except alerts.AlertError:
            return ""

    @Slot(str, str)
    def setupEmailAlerts(self, address: str, app_password: str) -> None:
        """Send a test email from `address` to itself; if it arrives, keep the app password and turn alerts on."""
        address = address.strip()
        try:
            alerts.provider_for(address)
        except alerts.AlertError as exc:
            self.dialogMessage.emit(str(exc), True)
            return
        if not alerts.clean_app_password(app_password):
            self.dialogMessage.emit("Enter the app password for that account.", True)
            return
        if self._mail_busy:
            return
        self._set_mail_busy(True)

        def work():
            alerts.send(address, app_password, alerts.compose(address, "test"))
            alerts.save_password(address, app_password)

        def done(_r):
            if self.prefs.alert_email and self.prefs.alert_email != address:
                old = self.prefs.alert_email
                self._mail_pool.submit(alerts.forget_password, old)
            self.prefs.alert_email, self.prefs.email_alerts = address, True
            prefsmod.save(self.prefs)
            self._set_mail_busy(False)
            self.dialogMessage.emit(f"Sent a test email to {address}. Email alerts are on.", False)

        self._run_mail(work, done, self._mail_failed)

    def _mail_failed(self, exc: Exception) -> None:
        self._set_mail_busy(False)
        if not isinstance(exc, alerts.AlertError):
            log.exception("Email alert setup failed", exc_info=exc)
        self.dialogMessage.emit(str(exc) if isinstance(exc, alerts.AlertError) else
                                "Couldn't send the test email. Details are in the log.", True)

    @Slot()
    def sendTestEmail(self) -> None:
        address = self.prefs.alert_email
        if not address or self._mail_busy:
            return
        self._set_mail_busy(True)

        def done(_r):
            self._set_mail_busy(False)
            self.dialogMessage.emit(f"Sent a test email to {address}.", False)

        self._run_mail(lambda: alerts.send(address, alerts.load_password(address), alerts.compose(address, "test")),
                       done, self._mail_failed)

    @Slot(bool)
    def setEmailAlerts(self, on: bool) -> None:
        self.prefs.email_alerts = bool(on) and bool(self.prefs.alert_email)
        prefsmod.save(self.prefs)
        self.alertsChanged.emit()

    @Slot()
    def removeEmailAlerts(self) -> None:
        address = self.prefs.alert_email
        self.prefs.alert_email, self.prefs.email_alerts = "", False
        prefsmod.save(self.prefs)
        self.alertsChanged.emit()
        if address:
            self._mail_pool.submit(alerts.forget_password, address)
        self.dialogMessage.emit("Email alerts are off, and the app password was removed from this computer.", False)

    def _alert(self, kind: str, **facts) -> None:
        """Email a security alert to the user's own address, in the background. Never blocks the app."""
        address = self.prefs.alert_email
        if not (self.prefs.email_alerts and address):
            return
        if kind in ("lockout", "leaks") and not self._alert_throttle.allow(kind):
            log.info("Skipped a %s alert: one was sent in the last 10 minutes.", kind)
            return

        def work():
            alerts.send(address, alerts.load_password(address), alerts.compose(address, kind, **facts))

        def failed(exc):
            log.warning("Couldn't send the %s alert: %s", kind, exc)
            if kind != "lockout":  # don't tell whoever is guessing passwords that an alert was attempted
                why = str(exc) if isinstance(exc, alerts.AlertError) else "Details are in the log."
                self.toast.emit(f"Couldn't send the security alert email. {why}")

        self._run_mail(work, lambda _r: log.info("Sent a %s alert.", kind), failed)

    @Slot(str)
    def importCsv(self, url: str) -> None:
        try:
            rows = csvio.read_csv(_local_path(url))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            self.dialogMessage.emit(f"Couldn't import: {exc}", True)
            return
        if not rows:
            self.dialogMessage.emit("That file has no passwords in it.", True)
            return

        def done(result):
            added, skipped = result
            message = f"Added {added} password{'s' if added != 1 else ''}."
            if skipped:
                message += f" Skipped {skipped} you already have or that had no name."
            self.dialogMessage.emit(message, False)
            self.reload()

        self._run(lambda: self.vault.import_entries(rows), done,
                  lambda exc: self.dialogMessage.emit(f"Couldn't import: {exc}", True))

    @Slot(str)
    def exportCsv(self, url: str) -> None:
        path = _local_path(url)

        def done(count):
            self.dialogMessage.emit(f"Saved {count} password{'s' if count != 1 else ''} to {path}.", False)

        self._run(lambda: csvio.write_csv(path, self.vault.entries()), done,
                  lambda exc: self.dialogMessage.emit(f"Couldn't export: {exc}", True))

    # ------------------------------------------------------- idle lock, quit

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt API)
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress,
                            QEvent.Type.Wheel):
            self._last_activity = time.monotonic()
        return False

    def _on_tick(self) -> None:
        if self._lockout_until:
            if time.monotonic() >= self._lockout_until:
                self._lockout_until = 0.0
            self.lockoutChanged.emit()
        minutes = self.prefs.auto_lock_minutes
        if (minutes and self.vault is not None and self.vault.is_unlocked
                and time.monotonic() - self._last_activity > minutes * 60):
            self.lock()

    @Slot()
    def shutdown(self) -> None:
        self._clear_clipboard()
        if self.vault is not None:
            self.vault.lock()
        conn = self._conn
        self._conn = None
        if conn is not None:
            try:
                self._pool.submit(conn.close).result(timeout=5)
            except Exception:  # noqa: BLE001 - closing on the way out
                pass
        self._pool.shutdown(wait=False)
        self._mail_pool.shutdown(wait=False)  # an alert that's on its way still finishes before the app exits
