"""Qt Quick interface: startup. The screens live in qml/, the logic behind them in backend.py."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, QSize, QtMsgType, QUrl, Slot, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from .backend import Backend

log = logging.getLogger(__name__)
HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
QML_DIR = HERE / "qml"
MAIN_QML = QML_DIR / "Main.qml"
APP_ICON = ASSETS / "app-icon.png"
ICON_DIR = ASSETS / "icon"
WINDOW_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
# The in-app icon's layers (qml/LiquidLock.qml) and the sharp small sizes, all made by packaging/make_icons.py.
ICON_FILES = [APP_ICON] + [ICON_DIR / f"{name}.png" for name in ("back", "shackle", "front")] + [
    ICON_DIR / f"app-{size}.png" for size in WINDOW_ICON_SIZES]
TITLE = "Password Manager"
APP_ID = "io.github.tgvenomyt.passwordmanager"  # the macOS bundle id; also the Windows taskbar id
DESKTOP_FILE = "password-manager"  # install.sh's password-manager.desktop on Linux


def _qt_messages(kind, _context, message: str) -> None:
    """Send Qt and QML warnings to our log (windowed builds have no console)."""
    if kind in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        log.error("Qt: %s", message)
    elif kind == QtMsgType.QtWarningMsg:
        log.warning("Qt: %s", message)


def app_icon() -> QIcon:
    """The app icon at every size, so title bars, taskbars and docks pick a sharp one."""
    icon = QIcon()
    for size in WINDOW_ICON_SIZES:
        icon.addFile(str(ICON_DIR / f"app-{size}.png"), QSize(size, size))
    icon.addFile(str(APP_ICON), QSize(512, 512))
    return icon


def _windows_taskbar_id() -> None:
    """Run from Python, Windows groups the window under python.exe and shows Python's icon on the
    taskbar. The built PasswordManager.exe carries icon.ico itself, so it's left alone there (an id of
    its own would split it from the pinned Start menu shortcut)."""
    if sys.platform != "win32" or getattr(sys, "frozen", False):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except (AttributeError, OSError):
        log.warning("Couldn't set the Windows taskbar id.", exc_info=True)


def make_app(argv: Optional[List[str]] = None) -> QGuiApplication:
    _windows_taskbar_id()  # must happen before the first window exists
    app = QGuiApplication.instance() or QGuiApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(TITLE)
    app.setApplicationDisplayName(TITLE)
    app.setOrganizationName("PasswordManager")
    # Linux (Wayland) finds the window's icon through the matching .desktop entry.
    app.setDesktopFileName(DESKTOP_FILE)
    # The built macOS app gets its Dock icon from icon.icns; everywhere else (Windows and Linux title
    # bars and taskbars, macOS when run from Python) uses this.
    if not (sys.platform == "darwin" and getattr(sys, "frozen", False)):
        app.setWindowIcon(app_icon())
    return app


class WindowTools(QObject):
    """What QML can't do itself: move and resize a window in one step. The macOS resize edges use it,
    because Qt can't hand a resize from inside the window over to macOS (it can for moving)."""

    @Slot(QObject, int, int, int, int)
    def setGeometry(self, window, x: int, y: int, width: int, height: int) -> None:  # noqa: N802 (Qt naming)
        window.setGeometry(x, y, width, height)


def load_ui(backend: Backend) -> Tuple[QQmlApplicationEngine, List[str]]:
    """Load Main.qml with `backend` exposed to it. Returns the engine and any QML warnings."""
    engine = QQmlApplicationEngine()
    problems: List[str] = []
    engine.warnings.connect(lambda warnings: problems.extend(w.toString() for w in warnings))
    engine.rootContext().setContextProperty("backend", backend)
    tools = WindowTools(engine)  # owned by the engine, so it lives exactly as long as the interface
    engine.rootContext().setContextProperty("windowTools", tools)
    engine.load(QUrl.fromLocalFile(str(MAIN_QML)))
    if not engine.rootObjects():
        problems.append(f"Couldn't load {MAIN_QML}")
    return engine, problems


def run() -> int:
    qInstallMessageHandler(_qt_messages)
    app = make_app()
    backend = Backend()
    engine, problems = load_ui(backend)
    for problem in problems:
        log.error("QML: %s", problem)
    if not engine.rootObjects():
        return 1
    backend.start()
    code = app.exec()
    del engine  # the interface goes before the backend it reads from
    backend.shutdown()
    return code


def self_test_ui() -> List[str]:
    """Load every screen off-screen and return any QML problems (used by --self-test and the tests)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    make_app([sys.argv[0] if sys.argv else "password-manager"])
    backend = Backend()
    engine, problems = load_ui(backend)
    if engine.rootObjects():
        for stage in ("unlock", "create", "recover", "noRecovery", "gpg", "recoveryKey", "fatal", "main"):
            backend._stage = stage
            backend.stageChanged.emit()
            QGuiApplication.processEvents()
    # Tear down the interface before the backend it reads from.
    for root in engine.rootObjects():
        root.setProperty("visible", False)
    engine.clearComponentCache()
    del engine
    QGuiApplication.processEvents()
    backend.shutdown()
    return [p for p in problems if "Shader" not in p]


def main() -> int:
    try:
        return run()
    except Exception:  # last resort: log it instead of dying silently
        log.exception("Unhandled error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
