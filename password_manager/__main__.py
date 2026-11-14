"""Entry point.

    python -m password_manager            launch the app
    python -m password_manager setup      first-time configuration (run by the installers)
    python -m password_manager --version
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import List, Optional

from . import __version__
from .config import config_dir


def _configure_logging() -> None:
    # Windowed builds (e.g. PasswordManager.exe) have no stderr at all.
    handlers: List[logging.Handler] = [logging.StreamHandler()] if sys.stderr else []
    try:
        log_dir = config_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_dir / "password-manager.log", maxBytes=512_000, backupCount=2, encoding="utf-8"
            )
        )
    except OSError:
        pass
    # Never log secrets: only events and errors are logged.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=handlers)


def self_test() -> int:
    """Check that every runtime piece loads. The installers run this on a freshly built binary."""
    import importlib
    import os
    import tkinter

    import bcrypt  # noqa: F401
    import mysql.connector  # noqa: F401

    from . import crypto
    from .app import ASSETS

    for plugin in ("caching_sha2_password", "mysql_native_password"):  # loaded dynamically by the connector
        importlib.import_module(f"mysql.connector.plugins.{plugin}")
    crypto.derive_kek("self-test", crypto.KdfParams(salt=b"\0" * 16, n=2**10))
    images = sorted(ASSETS.rglob("*.png"))
    if len(images) < 40:
        raise RuntimeError(f"missing GUI assets: found {len(images)} of 40 images in {ASSETS}")
    tkinter.Tcl().eval("info patchlevel")
    if sys.platform in ("darwin", "win32") or os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        root = tkinter.Tk()
        root.withdraw()
        tkinter.PhotoImage(master=root, file=str(images[0]))
        root.destroy()
    print(f"Password Manager {__version__}: self-test OK")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] in (["--version"], ["-V"]):
        print(f"Password Manager {__version__}")
        return 0
    if argv[:1] == ["--self-test"]:
        return self_test()
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__.strip())
        return 0
    _configure_logging()
    if argv[:1] == ["setup"]:
        from .setup_cli import main as setup_main

        return setup_main(argv[1:])
    if argv:
        print(f"Unknown arguments: {' '.join(argv)}\n\n{__doc__.strip()}", file=sys.stderr)
        return 2
    from .app import main as app_main

    return app_main()


if __name__ == "__main__":
    sys.exit(main())
